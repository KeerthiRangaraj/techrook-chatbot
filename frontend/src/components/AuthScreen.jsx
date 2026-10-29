import { useState } from 'react'

const S = {
  wrap: { minHeight:'100vh', background:'#020617', display:'flex', alignItems:'center', justifyContent:'center', padding:20 },
  card: { width:'100%', maxWidth:440, background:'rgba(15,23,42,0.97)', border:'1px solid rgba(56,189,248,0.18)', borderRadius:18, padding:'44px 40px', boxShadow:'0 0 80px rgba(56,189,248,0.07), 0 25px 50px rgba(0,0,0,0.5)' },
  logo: { textAlign:'center', marginBottom:36 },
  logoMark: { fontSize:32, marginBottom:8, display:'block' },
  logoText: { fontSize:24, fontWeight:700, color:'#38BDF8', letterSpacing:'-1px' },
  logoSub: { fontSize:10, color:'#475569', letterSpacing:4, textTransform:'uppercase', marginTop:5, display:'block' },
  h2: { fontSize:16, fontWeight:700, color:'#F1F5F9', marginBottom:28, textAlign:'center', letterSpacing:'-0.5px' },
  fieldWrap: { marginBottom:0 },
  label: { display:'block', fontSize:10, color:'#64748B', letterSpacing:2, textTransform:'uppercase', marginBottom:7, marginTop:18 },
  input: { width:'100%', background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.08)', borderRadius:9, padding:'11px 14px', color:'#F1F5F9', fontSize:13, outline:'none', fontFamily:'inherit', transition:'border 0.2s' },
  select: { width:'100%', background:'rgba(10,18,35,0.8)', border:'1px solid rgba(255,255,255,0.08)', borderRadius:9, padding:'11px 14px', color:'#F1F5F9', fontSize:13, outline:'none', fontFamily:'inherit' },
  btn: { width:'100%', marginTop:28, padding:'13px', background:'linear-gradient(135deg,#0EA5E9,#38BDF8)', border:'none', borderRadius:9, color:'#020617', fontWeight:700, fontSize:13, cursor:'pointer', fontFamily:'inherit', letterSpacing:0.5, transition:'opacity 0.2s' },
  linkBtn: { display:'block', textAlign:'center', background:'none', border:'none', color:'#38BDF8', cursor:'pointer', fontSize:12, fontFamily:'inherit', marginTop:20, textDecoration:'underline', textUnderlineOffset:3 },
  error: { background:'rgba(239,68,68,0.08)', border:'1px solid rgba(239,68,68,0.25)', borderRadius:7, padding:'9px 13px', fontSize:12, color:'#FCA5A5', marginTop:14 },
  hint: { fontSize:10, color:'#374151', textAlign:'center', marginTop:18, lineHeight:1.8 },
  divider: { borderTop:'1px solid rgba(255,255,255,0.05)', margin:'24px 0' },
  demoChip: { display:'inline-block', background:'rgba(56,189,248,0.06)', border:'1px solid rgba(56,189,248,0.12)', borderRadius:5, padding:'2px 8px', fontSize:10, color:'#7DD3FC', margin:'2px 3px', cursor:'pointer' },
}

export default function AuthScreen({ onLogin, onSignup }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name:'', email:'', password:'', grade:'L0' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await onLogin(form.email, form.password)
      } else {
        if (!form.email.endsWith('@techrook.in')) throw new Error('Must use a @techrook.in email address')
        await onSignup(form.name, form.email, form.password, form.grade)
      }
    } catch (err) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const fillDemo = (email) => setForm(f => ({ ...f, email, password: 'pass123' }))

  return (
    <div style={S.wrap}>
      <div style={S.card}>
        <div style={S.logo}>
          <span style={S.logoMark}>🏰</span>
          <div style={S.logoText}>TechRook</div>
          <span style={S.logoSub}>Policy Assistant · 2026</span>
        </div>

        <div style={S.h2}>{mode === 'login' ? 'Sign In to Continue' : 'Create Your Account'}</div>

        <form onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <>
              <label style={S.label}>Full Name</label>
              <input style={S.input} placeholder="Your Full Name" value={form.name} onChange={set('name')} required />
            </>
          )}
          <label style={S.label}>TechRook Email</label>
          <input style={S.input} type="email" placeholder="you@techrook.in" value={form.email} onChange={set('email')} required />
          <label style={S.label}>Password</label>
          <input style={S.input} type="password" placeholder="••••••••" value={form.password} onChange={set('password')} required />
          {mode === 'signup' && (
            <>
              <label style={S.label}>Grade Level</label>
              <select style={S.select} value={form.grade} onChange={set('grade')}>
                <option value="L0">L0 — Trainee / Intern</option>
                <option value="L1">L1 — Executive / Consultant</option>
                <option value="L2A">L2A — Senior Executive</option>
                <option value="L2B">L2B — Manager / Lead</option>
                <option value="L3">L3 — Director / SBU Head</option>
                <option value="L4">L4 — Executive Leadership</option>
              </select>
            </>
          )}
          {error && <div style={S.error}>⚠️ {error}</div>}
          <button type="submit" style={{ ...S.btn, opacity: loading ? 0.6 : 1 }} disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In →' : 'Create Account →'}
          </button>
        </form>

        {mode === 'login' && (
          <>
            <div style={S.divider} />
            <div style={{ textAlign:'center', fontSize:10, color:'#475569', marginBottom:8 }}>DEMO ACCOUNTS (password: pass123)</div>
            <div style={{ textAlign:'center' }}>
              {['alice@techrook.in','bob@techrook.in','carol@techrook.in'].map(e => (
                <span key={e} style={S.demoChip} onClick={() => fillDemo(e)}>{e.split('@')[0]}</span>
              ))}
            </div>
            <div style={{ textAlign:'center', fontSize:9, color:'#374151', marginTop:6 }}>
              alice=L0 Trainee · bob=L2A Employee · carol=L3 Director
            </div>
          </>
        )}

        <button style={S.linkBtn} onClick={() => { setMode(m => m==='login'?'signup':'login'); setError('') }}>
          {mode === 'login' ? 'New employee? Create account' : '← Back to Sign In'}
        </button>
      </div>
    </div>
  )
}
