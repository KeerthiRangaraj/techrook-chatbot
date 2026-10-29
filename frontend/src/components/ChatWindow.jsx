import { useState, useRef, useEffect, useCallback } from 'react'
import { chatAPI, conversationAPI } from '../api.js'

const ROLE_META = {
  'L0': { label: 'Trainee (L0)', color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', icon: '🎓' },
  'L1-L2': { label: 'Employee (L1–L2)', color: '#38BDF8', bg: 'rgba(56,189,248,0.1)', icon: '💼' },
  'L3+': { label: 'Manager (L3+)', color: '#F59E0B', bg: 'rgba(245,158,11,0.1)', icon: '🏆' },
}

const FAQ = {
  'L0': [
    { label: 'Leave Policy', q: 'What are my leave entitlements as a Trainee?' },
    { label: 'Certifications', q: 'What certifications must I complete in the first 15 days?' },
    { label: 'Documents Needed', q: 'What documents must I submit when joining TechRook?' },
    { label: 'Salary Day', q: 'When will my salary be credited each month?' },
    { label: 'POSH Policy', q: "What is TechRook's POSH policy and how do I report?" },
    { label: 'Attendance Rules', q: 'What are the attendance and late arrival rules?' },
  ],
  'L1-L2': [
    { label: 'PF & Gratuity', q: 'Explain PF deductions and gratuity eligibility.' },
    { label: 'Travel Allowances', q: 'What are my domestic travel entitlements by grade?' },
    { label: 'Performance Appraisal', q: 'How does the annual performance appraisal cycle work?' },
    { label: 'Notice Period', q: 'What is my notice period and buyout process?' },
    { label: 'WFH Stipend', q: 'Am I eligible for the WFH equipment stipend?' },
    { label: 'Referral Bonus', q: 'How does the employee referral bonus program work?' },
  ],
  'L3+': [
    { label: 'Disciplinary Levels', q: 'Explain the 4-level disciplinary process I can administer.' },
    { label: 'ICC & POSH', q: "What is TechRook's ICC composition and POSH complaint process?" },
    { label: 'BGV Process', q: 'What does the Background Verification process cover?' },
    { label: 'Performance Ratings', q: 'Explain the performance rating scale and bonus multipliers.' },
    { label: 'Spot Award', q: 'How do I give a Spot Recognition Award to my team?' },
    { label: 'Travel L3', q: 'What are my travel and accommodation entitlements as a Director?' },
  ],
}

function formatMsg(text) {
  return String(text || '').split('\n').map((line, i) => {
    if (line.startsWith('📋 Source:')) {
      return <div key={i} style={{ marginTop: 10, padding: '6px 11px', background: 'rgba(56,189,248,0.07)', borderLeft: '2px solid #38BDF8', borderRadius: '0 6px 6px 0', fontSize: 11, color: '#7DD3FC', fontStyle: 'italic' }}>{line}</div>
    }
    if (!line) return <div key={i} style={{ height: 6 }} />
    const bullet = line.startsWith('• ') || line.startsWith('- ')
    const parts = (bullet ? line.slice(2) : line).split(/\*\*(.*?)\*\*/g)
    return <div key={i} style={{ display: 'flex', gap: 8, paddingLeft: bullet ? 8 : 0, color: '#CBD5E1', marginBottom: 3, fontSize: 13, lineHeight: 1.7 }}>
      {bullet && <span style={{ color: '#38BDF8' }}>•</span>}
      <span>{parts.map((p, j) => j % 2 ? <strong key={j} style={{ color: '#F1F5F9' }}>{p}</strong> : p)}</span>
    </div>
  })
}

const makeWelcome = (user, pendingCount) => ({
  id: 'welcome',
  role: 'assistant',
  content: `Welcome back, **${user.name}**! 👋\n\nI'm your TechRook Policy Assistant. You're signed in as **${user.grade}** in the **${user.dept}** department.\n\n${pendingCount > 0 ? `⚠️ You have **${pendingCount} pending onboarding item(s)**. Click the checklist icon above to review them — some are time-sensitive!\n\n` : '✅ Your onboarding checklist is complete!\n\n'}Ask me anything about TechRook HR policies, benefits, or your onboarding.`,
})

const buttonStyle = {
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 8,
  color: '#CBD5E1',
  cursor: 'pointer',
  fontFamily: 'inherit',
}

export default function ChatWindow({ user, onOpenChecklist, onLogout, pendingCount }) {
  const [messages, setMessages] = useState([])
  const [conversations, setConversations] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const activeConversationRef = useRef(null)
  const loadingRef = useRef(false)
  const loadSequenceRef = useRef(0)
  const welcome = makeWelcome(user, pendingCount)
  const meta = ROLE_META[user.role] || ROLE_META.L0

  const refreshConversations = useCallback(async () => {
    const data = await conversationAPI.list()
    setConversations(data.conversations || [])
    return data.conversations || []
  }, [])

  const openConversation = useCallback(async (id) => {
    if (loadingRef.current) return
    const sequence = ++loadSequenceRef.current
    setLoadingHistory(true)
    setError('')
    try {
      const data = await conversationAPI.getMessages(id)
      if (sequence !== loadSequenceRef.current) return
      activeConversationRef.current = id
      setConversationId(id)
      setMessages((data.messages || []).map(m => ({
        id: m.id,
        role: m.role,
        content: m.message,
        verified: m.verified,
      })))
      setInput('')
    } catch (err) {
      if (sequence === loadSequenceRef.current) setError(`Could not open conversation: ${err.message}`)
    } finally {
      if (sequence === loadSequenceRef.current) setLoadingHistory(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const sequence = ++loadSequenceRef.current
    activeConversationRef.current = null
    setConversationId(null)
    setMessages([])
    setConversations([])
    setLoadingHistory(true)
    setError('')
    conversationAPI.list()
      .then(async data => {
        if (cancelled) return
        const list = data.conversations || []
        setConversations(list)
        if (list.length) {
          const id = list[0].id
          const response = await conversationAPI.getMessages(id)
          if (cancelled || sequence !== loadSequenceRef.current) return
          activeConversationRef.current = id
          setConversationId(id)
          setMessages((response.messages || []).map(m => ({
            id: m.id, role: m.role, content: m.message, verified: m.verified,
          })))
        }
      })
      .catch(err => { if (!cancelled) setError(`Unable to load chat history: ${err.message}`) })
      .finally(() => { if (!cancelled && sequence === loadSequenceRef.current) setLoadingHistory(false) })
    return () => { cancelled = true; ++loadSequenceRef.current }
  }, [user.email])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, loadingHistory])

  const newChat = () => {
    if (loadingRef.current || loadingHistory) return
    ++loadSequenceRef.current
    activeConversationRef.current = null
    setConversationId(null)
    setMessages([])
    setInput('')
    setError('')
    inputRef.current?.focus()
  }

  const send = async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || loadingRef.current || loadingHistory) return
    loadingRef.current = true
    setLoading(true)
    setInput('')
    setError('')
    const tempId = `pending-${Date.now()}`
    setMessages(p => [...p, { id: tempId, role: 'user', content: msg }])

    let id = activeConversationRef.current
    try {
      // Create the conversation only when its first message is sent.
      if (!id) {
        const created = await conversationAPI.create(msg.slice(0, 80))
        id = created.conversation.id
        activeConversationRef.current = id
        setConversationId(id)
      }
      const response = await chatAPI.send(msg, id)
      // Reload from the database to ensure the UI matches persisted messages.
      const saved = await conversationAPI.getMessages(id)
      setMessages((saved.messages || []).map(m => ({
        id: m.id,
        role: m.role,
        content: m.message,
        verified: m.verified,
      })))
      await refreshConversations()
    } catch (err) {
      setMessages(p => p.filter(m => m.id !== tempId))
      setInput(msg)
      setError(`Message not completed: ${err.message}. Check the conversation before retrying.`)
      // Refresh when possible; a partial save may already exist.
      if (id) {
        try {
          const saved = await conversationAPI.getMessages(id)
          setMessages((saved.messages || []).map(m => ({
            id: m.id, role: m.role, content: m.message, verified: m.verified,
          })))
          await refreshConversations()
        } catch { /* keep the visible error */ }
      }
    } finally {
      loadingRef.current = false
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const displayedMessages = messages.length ? messages : [welcome]

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', background: '#020617', color: '#F1F5F9', fontFamily: 'inherit' }}>
      <style>{`
        @keyframes fadeUp { from { opacity:0; transform:translateY(6px) } to { opacity:1; transform:translateY(0) } }
        @keyframes dot { 0%,60%,100% { transform:translateY(0); opacity:.4 } 30% { transform:translateY(-5px); opacity:1 } }
        textarea:focus { border-color:rgba(56,189,248,0.4) !important; outline:none }
      `}</style>

      {sidebarOpen && <aside style={{ width: 250, flexShrink: 0, borderRight: '1px solid rgba(255,255,255,0.08)', background: '#080F1E', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ padding: 14, borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <button onClick={newChat} disabled={loading || loadingHistory} style={{ ...buttonStyle, width: '100%', padding: '11px 12px', textAlign: 'left', fontWeight: 700, color: '#7DD3FC', opacity: loading || loadingHistory ? .5 : 1 }}>＋ New Chat</button>
        </div>
        <div style={{ padding: '16px 14px 8px', color: '#64748B', fontSize: 10, fontWeight: 700, letterSpacing: 1.3 }}>RECENT CONVERSATIONS</div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px 16px' }}>
          {conversations.length === 0 && <div style={{ padding: 12, fontSize: 12, color: '#64748B' }}>No saved conversations yet.</div>}
          {conversations.map(c => <button key={c.id} onClick={() => openConversation(c.id)} disabled={loading || loadingHistory} title={c.title} style={{ display: 'block', width: '100%', padding: '11px 12px', marginBottom: 4, textAlign: 'left', border: '1px solid transparent', borderRadius: 8, background: conversationId === c.id ? 'rgba(56,189,248,0.13)' : 'transparent', color: conversationId === c.id ? '#7DD3FC' : '#CBD5E1', cursor: loading || loadingHistory ? 'not-allowed' : 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12, fontFamily: 'inherit' }}>▤ {c.title}</button>)}
        </div>
      </aside>}

      <main style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, maxWidth: 1000, margin: '0 auto' }}>
        <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(8,15,30,0.97)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
            <button onClick={() => setSidebarOpen(v => !v)} title="Toggle chat history" style={{ ...buttonStyle, padding: '7px 10px' }}>☰</button>
            <span style={{ fontSize: 21 }}>🏰</span>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.5px' }}>TechRook Policy Assistant</div>
              <div style={{ fontSize: 10, color: '#64748B' }}>{user.name} · {user.grade} · {user.dept}</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ padding: '5px 8px', borderRadius: 20, background: meta.bg, color: meta.color, fontSize: 10, whiteSpace: 'nowrap' }}>{meta.icon} {meta.label}</span>
            <button title="Onboarding Checklist" onClick={onOpenChecklist} style={{ ...buttonStyle, padding: '7px 9px', position: 'relative' }}>☑️{pendingCount > 0 && <span style={{ position: 'absolute', top: -6, right: -5, background: '#F59E0B', color: '#020617', borderRadius: 20, padding: '1px 5px', fontSize: 9 }}>{pendingCount}</span>}</button>
            <button title="Sign Out" onClick={onLogout} style={{ ...buttonStyle, padding: '8px 10px', fontSize: 11 }}>Sign Out</button>
          </div>
        </header>

        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 8px' }}>
          {loadingHistory ? <div style={{ color: '#94A3B8', fontSize: 13 }}>Loading conversation…</div> : displayedMessages.map(m => <div key={m.id} style={{ animation: 'fadeUp .22s ease', display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 16 }}>
            {m.role === 'user' ? <div style={{ maxWidth: '72%', background: 'linear-gradient(135deg,#0EA5E9,#0369A1)', borderRadius: '16px 16px 4px 16px', padding: '12px 16px', fontSize: 13, lineHeight: 1.7, color: '#fff', overflowWrap: 'anywhere' }}>{m.content}</div> : <div style={{ maxWidth: '82%', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '16px 16px 16px 4px', padding: '14px 16px', overflowWrap: 'anywhere' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}><span>🏰</span><span style={{ fontSize: 10, color: '#64748B', fontWeight: 700, letterSpacing: 1.5 }}>POLICY ASSISTANT</span></div>
              {formatMsg(m.content)}
            </div>}
          </div>)}
          {loading && <div style={{ display: 'flex', gap: 6, padding: 12 }}>{[0, 1, 2].map(i => <div key={i} style={{ width: 7, height: 7, borderRadius: '50%', background: '#38BDF8', animation: `dot 1.2s ease ${i * .18}s infinite` }} />)}</div>}
          <div ref={bottomRef} />
        </div>

        {error && <div role="alert" style={{ margin: '0 20px 8px', padding: '10px 12px', borderRadius: 8, background: 'rgba(239,68,68,.10)', border: '1px solid rgba(239,68,68,.25)', color: '#FCA5A5', fontSize: 12 }}>{error}</div>}

        <div style={{ padding: '8px 20px', borderTop: '1px solid rgba(255,255,255,0.04)', display: 'flex', gap: 8, overflowX: 'auto', flexShrink: 0, background: 'rgba(8,15,30,0.6)' }}>
          <span style={{ fontSize: 10, color: '#64748B', alignSelf: 'center', flexShrink: 0 }}>Quick:</span>
          {(FAQ[user.role] || FAQ.L0).map(f => <button key={f.label} onClick={() => send(f.q)} disabled={loading || loadingHistory} style={{ padding: '5px 12px', borderRadius: 20, background: 'rgba(56,189,248,0.07)', border: '1px solid rgba(56,189,248,0.18)', color: '#7DD3FC', fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0, fontFamily: 'inherit', opacity: loading || loadingHistory ? .5 : 1 }}>{f.label}</button>)}
        </div>

        <div style={{ display: 'flex', gap: 10, padding: '12px 20px 16px', borderTop: '1px solid rgba(255,255,255,0.05)', background: 'rgba(8,15,30,0.97)', flexShrink: 0 }}>
          <textarea ref={inputRef} rows={1} style={{ flex: 1, minWidth: 0, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: '11px 16px', color: '#F1F5F9', fontSize: 13, fontFamily: 'inherit', resize: 'none', lineHeight: 1.5 }} placeholder="Ask about leaves, salary, POSH, travel, certifications…" value={input} disabled={loading || loadingHistory} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
          <button onClick={() => send()} disabled={loading || loadingHistory || !input.trim()} style={{ background: 'linear-gradient(135deg,#0EA5E9,#38BDF8)', border: 'none', borderRadius: 10, padding: '11px 20px', color: '#020617', fontWeight: 700, cursor: 'pointer', fontSize: 18, opacity: loading || loadingHistory || !input.trim() ? .45 : 1 }}>↑</button>
        </div>
      </main>
    </div>
  )
}
