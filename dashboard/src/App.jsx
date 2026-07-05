import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Dashboard from './pages/Dashboard'
import Groups from './pages/Groups'
import News from './pages/News'
import Questions from './pages/Questions'
import StudyPlans from './pages/StudyPlans'
import ScheduledPosts from './pages/ScheduledPosts'
import Responses from './pages/Responses'
import BannedUsers from './pages/BannedUsers'
import ActivityLog from './pages/ActivityLog'
import Settings from './pages/Settings'
import Login from './pages/Login'
import './App.css'

const pageTitles = {
  '/': { title: 'لوحة التحكم', subtitle: 'نظرة عامة على أداء البوت' },
  '/groups': { title: 'إدارة القروبات', subtitle: 'التحكم في قروبات البوت' },
  '/news': { title: 'الأخبار', subtitle: 'إدارة أخبار البوت' },
  '/questions': { title: 'الأسئلة', subtitle: 'إدارة أسئلة البوت الشائعة' },
  '/study-plans': { title: 'الخطط الدراسية', subtitle: 'إدارة الخطط الدراسية والمجموعات' },
  '/scheduled-posts': { title: 'النشر المجدول', subtitle: 'إدارة المنشورات المجدولة' },
  '/responses': { title: 'الردود', subtitle: 'إدارة ردود البوت' },
  '/banned': { title: 'المحظورين', subtitle: 'إدارة المستخدمين المحظورين' },
  '/activity': { title: 'سجل النشاطات', subtitle: 'تتبع جميع أنشطة البوت' },
  '/settings': { title: 'الإعدادات', subtitle: 'تخصيص إعدادات البوت' },
}

function Layout({ sidebarOpen, setSidebarOpen }) {
  const location = useLocation()
  const { title, subtitle } = pageTitles[location.pathname] || { title: '', subtitle: '' }

  return (
    <div className="app">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="main-content">
        <Header title={title} subtitle={subtitle} onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/groups" element={<Groups />} />
            <Route path="/news" element={<News />} />
            <Route path="/questions" element={<Questions />} />
            <Route path="/study-plans" element={<StudyPlans />} />
            <Route path="/scheduled-posts" element={<ScheduledPosts />} />
            <Route path="/responses" element={<Responses />} />
            <Route path="/banned" element={<BannedUsers />} />
            <Route path="/activity" element={<ActivityLog />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return localStorage.getItem('isLoggedIn') === 'true'
  })
  const [sidebarOpen, setSidebarOpen] = useState(false)

  if (!isLoggedIn) {
    return <Login onLogin={() => setIsLoggedIn(true)} />
  }

  return (
    <Router>
      <Layout sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
    </Router>
  )
}

export default App
