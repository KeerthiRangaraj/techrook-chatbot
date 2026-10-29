import { useEffect, useState } from 'react'
import { checklistAPI } from '../api.js'

const ITEMS = [
  { id:'docs',       icon:'📁', label:'Upload Documents',             desc:'Aadhaar, PAN & Relieving Letter',        chapter:'Ch. 8.1',  urgent:true },
  { id:'icici',      icon:'🏦', label:'Open ICICI Power Pay Account', desc:'Salary account activation on Day 1',     chapter:'Ch. 11',   urgent:true },
  { id:'cybervault', icon:'🛡️', label:'CyberVault Basics Cert',      desc:'Complete within 15 days of joining',     chapter:'Ch. 9.1',  urgent:true },
  { id:'aiethics',   icon:'🤖', label:'AI Ethics 101 Cert',           desc:'Complete within 15 days of joining',     chapter:'Ch. 9.2',  urgent:true },
  { id:'posh',       icon:'⚖️', label:'Acknowledge POSH Policy',      desc:'Anti-Harassment briefing acknowledgement',chapter:'Ch. 26',  urgent:false },
  { id:'mfa',        icon:'🔐', label:'Enroll MFA Devices',           desc:'Min. 2 devices within 3 working days',   chapter:'Ch. 23.1', urgent:true },
]

export default function ChecklistPanel({ onClose }) {
  const [state, setState] = useState({})
  const [saving, setSaving] = useState(null)

  useEffect(() => {
    checklistAPI.get().then(d => setState(d.checklist || {})).catch(() => {})
  }, [])

  const toggle = async (id) => {
    const next = !state[id]
    setState(s => ({ ...s, [id]: next }))
    setSaving(id)
    try { await checklistAPI.update(id, next) } catch {}
    setSaving(null)
  }

  const done = ITEMS.filter(i => state[i.id]).length
  const pct = Math.round((done / ITEMS.length) * 100)
  const pending = ITEMS.filter(i => !state[i.id])

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.75)', backdropFilter:'blur(5px)', zIndex:200, display:'flex', alignItems:'flex-end', justifyContent:'center' }} onClick={onClose}>
      <div style={{ width:'100%', maxWidth:900, background:'#0B1628', border:'1px solid rgba(255,255,255,0.07)', borderRadius:'18px 18px 0 0', padding:'28px 28px 40px', maxHeight:'82vh', overflowY:'auto' }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:24 }}>
          <div>
            <div style={{ fontSize:17, fontWeight:700, color:'#F1F5F9' }}>🗂️ Onboarding Checklist</div>
            <div style={{ fontSize:11, color:'#64748B', marginTop:3 }}>{done} of {ITEMS.length} complete · {pct}% done</div>
          </div>
          <button onClick={onClose} style={{ background:'rgba(255,255,255,0.05)', border:'1px solid rgba(255,255,255,0.08)', borderRadius:8, padding:'6px 12px', color:'#94A3B8', cursor:'pointer', fontSize:14 }}>✕ Close</button>
        </div>

        {/* Progress bar */}
        <div style={{ height:5, background:'rgba(255,255,255,0.05)', borderRadius:3, marginBottom:24, overflow:'hidden' }}>
          <div style={{ height:'100%', width:`${pct}%`, background:'linear-gradient(90deg,#0EA5E9,#4ADE80)', borderRadius:3, transition:'width 0.5s ease' }} />
        </div>

        {/* Items */}
        {ITEMS.map(item => {
          const done = !!state[item.id]
          return (
            <div key={item.id} onClick={() => toggle(item.id)} style={{ display:'flex', alignItems:'center', gap:14, padding:'14px 16px', background: done ? 'rgba(74,222,128,0.04)' : 'rgba(255,255,255,0.02)', border:`1px solid ${done ? 'rgba(74,222,128,0.2)' : 'rgba(255,255,255,0.05)'}`, borderRadius:11, marginBottom:10, cursor:'pointer', transition:'all 0.2s', userSelect:'none' }}>
              <div style={{ width:24, height:24, borderRadius:7, border:`2px solid ${done ? '#4ADE80' : 'rgba(255,255,255,0.18)'}`, background: done ? '#4ADE80' : 'transparent', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, transition:'all 0.2s' }}>
                {saving === item.id ? <div style={{ width:10, height:10, border:'2px solid #020617', borderTop:'2px solid transparent', borderRadius:'50%', animation:'spin 0.6s linear infinite' }} /> : done ? <span style={{ color:'#020617', fontSize:13, fontWeight:700 }}>✓</span> : null}
              </div>
              <div style={{ fontSize:20, flexShrink:0 }}>{item.icon}</div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontSize:14, fontWeight:600, color: done ? '#4ADE80' : '#F1F5F9', textDecoration: done ? 'line-through' : 'none', display:'flex', alignItems:'center', gap:8 }}>
                  {item.label}
                  {item.urgent && !done && <span style={{ fontSize:9, background:'rgba(245,158,11,0.15)', border:'1px solid rgba(245,158,11,0.3)', color:'#FCD34D', borderRadius:4, padding:'1px 5px', fontWeight:700 }}>MANDATORY</span>}
                </div>
                <div style={{ fontSize:11, color:'#475569', marginTop:2 }}>{item.desc} · <span style={{ color:'#38BDF8' }}>{item.chapter}</span></div>
              </div>
            </div>
          )
        })}

        {/* Warning if pending urgent */}
        {pending.filter(i => i.urgent).length > 0 && (
          <div style={{ marginTop:18, padding:'13px 16px', background:'rgba(245,158,11,0.07)', border:'1px solid rgba(245,158,11,0.2)', borderRadius:10, fontSize:12, color:'#FCD34D', lineHeight:1.6 }}>
            ⚠️ <strong>{pending.filter(i=>i.urgent).length} mandatory item(s) pending.</strong> Certifications must be completed within 15 days of joining — failure will be recorded in your probation assessment (Chapter 9, TechRook Employee Handbook 2026).
          </div>
        )}
        {done === ITEMS.length && (
          <div style={{ marginTop:18, padding:'13px 16px', background:'rgba(74,222,128,0.07)', border:'1px solid rgba(74,222,128,0.2)', borderRadius:10, fontSize:12, color:'#4ADE80' }}>
            🎉 <strong>All onboarding tasks complete!</strong> Welcome to TechRook.
          </div>
        )}
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
