import { useState, useEffect } from 'react'
import { useAuth } from './hooks/useAuth.js'
import { checklistAPI } from './api.js'
import AuthScreen from './components/AuthScreen.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import ChecklistPanel from './components/ChecklistPanel.jsx'

const CHECKLIST_ITEMS = ['docs','icici','cybervault','aiethics','posh','mfa']

export default function App() {
  const { user, loading, login, signup, logout } = useAuth()
  const [showChecklist, setShowChecklist] = useState(false)
  const [checklistState, setChecklistState] = useState({})

  // Load checklist on login
  useEffect(() => {
    if (!user) return
    checklistAPI.get()
      .then(d => setChecklistState(d.checklist || {}))
      .catch(() => {})
  }, [user])

  const pendingCount = CHECKLIST_ITEMS.filter(id => !checklistState[id]).length

  if (loading) return (
    <div style={{ minHeight:'100vh', background:'#020617', display:'flex', alignItems:'center', justifyContent:'center' }}>
      <div style={{ textAlign:'center' }}>
        <div style={{ fontSize:36, marginBottom:16 }}>🏰</div>
        <div style={{ fontSize:13, color:'#475569', fontFamily:"'Space Mono', monospace" }}>Loading TechRook…</div>
      </div>
    </div>
  )

  if (!user) return <AuthScreen onLogin={login} onSignup={signup} />

  return (
    <>
      <ChatWindow
        user={user}
        pendingCount={pendingCount}
        onOpenChecklist={() => setShowChecklist(true)}
        onLogout={logout}
      />
      {showChecklist && (
        <ChecklistPanel
          onClose={() => {
            setShowChecklist(false)
            // Refresh checklist count after closing
            checklistAPI.get().then(d => setChecklistState(d.checklist || {})).catch(()=>{})
          }}
        />
      )}
    </>
  )
}
