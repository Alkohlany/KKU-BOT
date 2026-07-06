import React, { createContext, useContext, useState, useCallback } from 'react'

const ConfirmContext = createContext()

export function ConfirmProvider({ children }) {
  const [state, setState] = useState(null)

  const confirm = useCallback((message) => {
    return new Promise((resolve) => {
      setState({ message, resolve })
    })
  }, [])

  const handleConfirm = useCallback(() => {
    if (state) {
      state.resolve(true)
      setState(null)
    }
  }, [state])

  const handleCancel = useCallback(() => {
    if (state) {
      state.resolve(false)
      setState(null)
    }
  }, [state])

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {state && (
        <div className="modal-overlay" onClick={handleCancel}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <h3>تأكيد</h3>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 14, color: 'var(--gray-600)', lineHeight: 1.6 }}>
                {state.message}
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleConfirm}>
                تأكيد
              </button>
              <button className="btn btn-secondary" onClick={handleCancel}>
                إلغاء
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  )
}

export const useConfirm = () => useContext(ConfirmContext)
