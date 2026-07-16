const { Client } = require('pg');

const SOURCE = {
  host: 'dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com',
  user: 'kkubotdb_p064_user',
  password: 'ZEm3VYlQ5JQNGer1BIYlwWo0ZKpmAZCo',
  database: 'kku_bot',
  port: 5432,
  ssl: { rejectUnauthorized: false },
};

const DEST = {
  host: 'roundhouse.proxy.rlwy.net',
  user: 'postgres',
  password: 'ilXBPGUbAKhmSqwQtTPxPsjslKepTsBg',
  database: 'railway',
  port: 5432,
  ssl: { rejectUnauthorized: false },
};

async function getTables(client) {
  const res = await client.query(`
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename
  `);
  return res.rows.map(r => r.tablename);
}

async function getTableColumns(client, table) {
  const res = await client.query(`
    SELECT column_name, data_type, is_nullable, column_default,
           character_maximum_length, numeric_precision
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = $1
    ORDER BY ordinal_position
  `, [table]);
  return res.rows;
}

async function getRowCount(client, table) {
  const res = await client.query(`SELECT COUNT(*) AS count FROM "${table}"`);
  return parseInt(res.rows[0].count);
}

async function dumpTable(client, table) {
  const res = await client.query(`SELECT * FROM "${table}"`);
  return res.rows;
}

function buildInsert(table, columns, rows) {
  if (rows.length === 0) return '';
  const cols = rows[0].map(c => `"${c}"`).join(', ');
  const placeholders = rows[0].map((_, i) => `$${i + 1}`).join(', ');
  const stmt = `INSERT INTO "${table}" (${cols}) VALUES (${placeholders})`;
  return { stmt, rows };
}

async function resetSequences(destClient, table, maxId) {
  if (maxId > 0) {
    await destClient.query(`SELECT setval('"${table}_id_seq"', $1)`, [maxId]);
  }
}

async function main() {
  const src = new Client(SOURCE);
  const dst = new Client(DEST);

  console.log('Connecting to Render (source)...');
  await src.connect();
  console.log('Connected to Render.');

  console.log('Connecting to Railway (destination)...');
  try {
    await dst.connect();
    console.log('Connected to Railway.');
  } catch (e) {
    console.error('Failed to connect to Railway:', e.message);
    console.log('\nTrying alternate Railway host patterns...');
    // Try other common Railway proxy patterns
    const altHosts = [
      { host: 'roundhouse.proxy.rlwy.net', port: 5432 },
      { host: 'roundhouse.proxy.rlwy.net', port: 15432 },
      { host: 'containers-us-west-175.railway.app', port: 5432 },
    ];
    let connected = false;
    for (const alt of altHosts) {
      try {
        dst.host = alt.host;
        dst.port = alt.port;
        await dst.connect();
        console.log(`Connected to Railway at ${alt.host}:${alt.port}`);
        connected = true;
        break;
      } catch (e2) {
        console.log(`  Failed: ${alt.host}:${alt.port} - ${e2.message}`);
      }
    }
    if (!connected) {
      console.error('Could not connect to Railway. Exiting.');
      await src.end();
      process.exit(1);
    }
  }

  // Get tables from source
  const tables = await getTables(src);
  console.log(`\nFound ${tables.length} tables: ${tables.join(', ')}`);

  // Disable foreign key checks on dest
  await dst.query('SET session_replication_role = replica');

  for (const table of tables) {
    console.log(`\n--- Migrating: ${table} ---`);

    // Get schema
    const columns = await getTableColumns(src, table);

    // Get data
    const rows = await dumpTable(src, table);
    const count = rows.length;
    console.log(`  Source rows: ${count}`);

    if (count === 0) {
      // Create empty table on dest
      const colDefs = columns.map(c => {
        let def = `"${c.column_name}" ${c.data_type}`;
        if (c.character_maximum_length) def = `"${c.column_name}" ${c.data_type}(${c.character_maximum_length})`;
        if (c.is_nullable === 'NO') def += ' NOT NULL';
        if (c.column_default) def += ` DEFAULT ${c.column_default}`;
        return def;
      }).join(', ');
      await dst.query(`CREATE TABLE IF NOT EXISTS "${table}" (${colDefs})`);
      console.log(`  Created empty table.`);
      continue;
    }

    // Get column names from data
    const colNames = Object.keys(rows[0]);

    // Create table on dest
    const colDefs = columns.map(c => {
      let type = c.data_type;
      if (c.character_maximum_length && !['text', 'json', 'jsonb'].includes(c.data_type)) {
        type = `${c.data_type}(${c.character_maximum_length})`;
      }
      let def = `"${c.column_name}" ${type}`;
      if (c.is_nullable === 'NO') def += ' NOT NULL';
      if (c.column_default) def += ` DEFAULT ${c.column_default}`;
      return def;
    }).join(', ');
    await dst.query(`CREATE TABLE IF NOT EXISTS "${table}" (${colDefs})`);

    // Truncate dest table
    await dst.query(`TRUNCATE "${table}" CASCADE`);

    // Insert in batches
    const batchSize = 500;
    for (let i = 0; i < rows.length; i += batchSize) {
      const batch = rows.slice(i, i + batchSize);
      const placeholders = batch.map((row, ri) => {
        const vals = colNames.map((_, ci) => `$${ri * colNames.length + ci + 1}`);
        return `(${vals.join(', ')})`;
      }).join(', ');

      const flatValues = batch.flatMap(row =>
        colNames.map(c => row[c] === undefined ? null : row[c])
      );

      await dst.query(
        `INSERT INTO "${table}" (${colNames.map(c => `"${c}"`).join(', ')}) VALUES ${placeholders}`,
        flatValues
      );
    }

    // Reset sequence if table has id column
    if (colNames.includes('id')) {
      const maxId = Math.max(...rows.map(r => r.id).filter(v => v != null));
      if (maxId > 0) {
        try {
          await dst.query(`SELECT setval(pg_get_serial_sequence('"${table}"', 'id'), $1)`, [maxId]);
        } catch (e) {
          // Table might not have a serial sequence, that's ok
        }
      }
    }

    const destCount = await getRowCount(dst, table);
    console.log(`  Dest rows: ${destCount} ${destCount === count ? '✓' : '✗ MISMATCH'}`);
  }

  // Re-enable foreign key checks
  await dst.query('SET session_replication_role = origin');

  // Verify
  console.log('\n=== VERIFICATION ===');
  const destTables = await getTables(dst);
  console.log(`Railway tables: ${destTables.length}`);
  for (const table of destTables) {
    const count = await getRowCount(dst, table);
    console.log(`  ${table}: ${count} rows`);
  }

  await src.end();
  await dst.end();
  console.log('\nMigration complete.');
}

main().catch(e => { console.error(e); process.exit(1); });
