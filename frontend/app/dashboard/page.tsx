'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

type Reservation = {
  id: number
  client_name: string
  phone: string
  date: string
  time: string
  pax: number
  status: 'confirmed' | 'pending' | 'cancelled' | 'completed'
  table_name: string | null
  event_type: string
  vip_level: string
  requested_cava: boolean
  special_flag: boolean
  notes?: string
  admin_notes?: string
}

const STATUS = {
  confirmed: { label: 'Confirmada', color: '#1a1a1a', bg: '#d4f4dd', dot: '#2d9e4f' },
  pending:   { label: 'Pendiente',  color: '#1a1a1a', bg: '#fef3c7', dot: '#d97706' },
  cancelled: { label: 'Cancelada',  color: '#888',    bg: '#f0f0f0', dot: '#aaa'    },
  completed: { label: 'Completada', color: '#1a1a1a', bg: '#e0e7ff', dot: '#4f46e5' },
} as const

const FILTERS = [
  { value: 'all',       label: 'Todas'       },
  { value: 'confirmed', label: 'Confirmadas' },
  { value: 'pending',   label: 'Pendientes'  },
  { value: 'cancelled', label: 'Canceladas'  },
]

const ACTIONS: Record<string, { status: string; label: string; primary: boolean }[]> = {
  pending:   [
    { status: 'confirmed', label: 'Confirmar reserva', primary: true  },
    { status: 'cancelled', label: 'Cancelar',          primary: false },
  ],
  confirmed: [
    { status: 'completed', label: 'Marcar completada', primary: true  },
    { status: 'cancelled', label: 'Cancelar',          primary: false },
  ],
  cancelled: [
    { status: 'pending',   label: 'Reactivar',         primary: true  },
  ],
  completed: [],
}

export default function DashboardPage() {
  const router = useRouter()
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [loading, setLoading]           = useState(true)
  const [filter, setFilter]             = useState('all')
  const [date, setDate]                 = useState(() => new Date().toISOString().split('T')[0])
  const [selected, setSelected]         = useState<Reservation | null>(null)
  const [adminNote, setAdminNote]       = useState('')
  const [updating, setUpdating]         = useState(false)
  const [updateMsg, setUpdateMsg]       = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { router.push('/'); return }
    fetchReservations(token)
  }, [date])

  async function fetchReservations(token?: string) {
    setLoading(true)
    const t = token || localStorage.getItem('token')
    try {
      const res = await fetch(`http://localhost:8000/reservations/?date=${date}`, {
        headers: { Authorization: `Bearer ${t}` }
      })
      if (res.status === 401) { router.push('/'); return }
      setReservations(await res.json())
    } catch { /* offline */ }
    finally  { setLoading(false) }
  }

  function openPanel(r: Reservation) {
    setSelected(r)
    setAdminNote(r.admin_notes ?? '')
    setUpdateMsg(null)
  }

  function closePanel() {
    setSelected(null)
    setUpdateMsg(null)
  }

  async function changeStatus(newStatus: string) {
    if (!selected) return
    setUpdating(true)
    setUpdateMsg(null)
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`http://localhost:8000/reservations/${selected.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status: newStatus, admin_notes: adminNote || undefined })
      })
      if (res.ok) {
        setUpdateMsg({ ok: true, text: 'Actualizado correctamente' })
        const updated = { ...selected, status: newStatus as Reservation['status'], admin_notes: adminNote }
        setReservations(prev => prev.map(r => r.id === selected.id ? updated : r))
        setSelected(updated)
      } else {
        const err = await res.json()
        setUpdateMsg({ ok: false, text: err.detail ?? 'Error al actualizar' })
      }
    } catch {
      setUpdateMsg({ ok: false, text: 'No se pudo conectar con el servidor' })
    } finally {
      setUpdating(false)
    }
  }

  async function cancelReservation() {
    if (!selected) return
    setUpdating(true)
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`http://localhost:8000/reservations/${selected.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setUpdateMsg({ ok: true, text: 'Reserva cancelada' })
        const updated = { ...selected, status: 'cancelled' as Reservation['status'] }
        setReservations(prev => prev.map(r => r.id === selected.id ? updated : r))
        setSelected(updated)
      }
    } catch {
      setUpdateMsg({ ok: false, text: 'Error al cancelar' })
    } finally {
      setUpdating(false)
    }
  }

  function logout() {
    localStorage.removeItem('token')
    router.push('/')
  }

  const visible = filter === 'all' ? reservations : reservations.filter(r => r.status === filter)

  const stats = {
    total:     reservations.length,
    confirmed: reservations.filter(r => r.status === 'confirmed').length,
    pending:   reservations.filter(r => r.status === 'pending').length,
    pax:       reservations.filter(r => r.status !== 'cancelled').reduce((s, r) => s + r.pax, 0),
  }

  const dateLabel = new Date(date + 'T12:00:00').toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long'
  })

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0a0a0a', fontFamily: 'var(--font-body)' }}>

      {/* ── SIDEBAR ── */}
      <aside style={{
        width: '200px', background: '#0f0f0f', borderRight: '1px solid #222',
        padding: '28px 16px', display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        <div style={{ marginBottom: '32px', textAlign: 'center' }}>
          <Image src="/logo.png" alt="MM" width={90} height={90} style={{ borderRadius: '4px' }} />
        </div>
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{
            background: '#1a1a1a', color: '#fff', fontSize: '13px', fontWeight: 500,
            padding: '10px 14px', borderRadius: '6px', cursor: 'pointer',
          }}>
            Reservas
          </div>
          <div onClick={() => router.push('/dashboard/mesas')}
            style={{ color: '#666', fontSize: '13px', padding: '10px 14px', borderRadius: '6px', cursor: 'pointer', transition: 'all 0.15s' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#1a1a1a'; e.currentTarget.style.color = '#fff' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#666' }}>
            Mesas
          </div>
        </nav>
        <button onClick={logout}
          style={{ background: '#1a1a1a', border: 'none', color: '#666', padding: '10px', fontSize: '12px', borderRadius: '6px', cursor: 'pointer', fontFamily: 'var(--font-body)', transition: 'color 0.2s' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
          onMouseLeave={e => (e.currentTarget.style.color = '#666')}>
          Cerrar sesión
        </button>
      </aside>

      {/* ── MAIN ── */}
      <main style={{ flex: 1, padding: '36px 40px', overflowY: 'auto', minWidth: 0 }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
          <div>
            <p style={{ color: '#555', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '6px' }}>
              Reservas del día
            </p>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '36px', color: '#fff', fontWeight: 300, textTransform: 'capitalize' }}>
              {dateLabel}
            </h2>
          </div>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            style={{ background: '#1a1a1a', border: '1px solid #333', color: '#fff', padding: '10px 14px', fontSize: '14px', outline: 'none', borderRadius: '6px', fontFamily: 'var(--font-body)', cursor: 'pointer' }}
            onFocus={e => (e.target.style.borderColor = '#555')}
            onBlur={e  => (e.target.style.borderColor = '#333')} />
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px', marginBottom: '32px' }}>
          {[
            { label: 'Total',      value: stats.total,     accent: '#fff'    },
            { label: 'Confirmadas', value: stats.confirmed, accent: '#2d9e4f' },
            { label: 'Pendientes', value: stats.pending,   accent: '#d97706' },
            { label: 'Cubiertos',  value: stats.pax,       accent: '#fff'    },
          ].map(s => (
            <div key={s.label} style={{ background: '#141414', border: '1px solid #222', padding: '18px 20px', borderRadius: '8px' }}>
              <p style={{ color: '#666', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '8px' }}>
                {s.label}
              </p>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '44px', color: s.accent, fontWeight: 300, lineHeight: 1 }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Filtros */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '20px' }}>
          {FILTERS.map(f => (
            <button key={f.value} onClick={() => setFilter(f.value)} style={{
              background:  filter === f.value ? '#fff' : '#141414',
              color:       filter === f.value ? '#0a0a0a' : '#888',
              border:      `1px solid ${filter === f.value ? '#fff' : '#333'}`,
              padding: '7px 16px', fontSize: '12px', borderRadius: '5px',
              cursor: 'pointer', fontFamily: 'var(--font-body)', fontWeight: filter === f.value ? 500 : 400,
              transition: 'all 0.15s',
            }}>
              {f.label}
            </button>
          ))}
        </div>

        {/* Tabla */}
        {loading ? (
          <p style={{ color: '#555', fontSize: '14px', paddingTop: '40px' }}>Cargando reservas...</p>
        ) : visible.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '28px', color: '#333', fontWeight: 300 }}>
              Sin reservas para este día
            </p>
          </div>
        ) : (
          <div style={{ background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: '8px', overflow: 'hidden' }}>
            {/* Header tabla */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 80px 60px 100px 120px 120px', gap: '0', borderBottom: '1px solid #1e1e1e', padding: '10px 20px' }}>
              {['Cliente', 'Hora', 'Pax', 'Mesa', 'Ocasión', 'Estado'].map(col => (
                <span key={col} style={{ color: '#555', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 500 }}>
                  {col}
                </span>
              ))}
            </div>
            {/* Filas */}
            {visible.map((r, i) => {
              const s = STATUS[r.status] ?? STATUS.cancelled
              const isSelected = selected?.id === r.id
              return (
                <div key={r.id} onClick={() => openPanel(r)}
                  style={{
                    display: 'grid', gridTemplateColumns: '2fr 80px 60px 100px 120px 120px',
                    gap: '0', padding: '14px 20px', cursor: 'pointer',
                    borderBottom: i < visible.length - 1 ? '1px solid #161616' : 'none',
                    background: isSelected ? '#1a1a1a' : 'transparent',
                    borderLeft: `3px solid ${isSelected ? '#fff' : 'transparent'}`,
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#141414' }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}>

                  <div>
                    <div style={{ color: '#fff', fontSize: '15px', fontWeight: 400, marginBottom: '2px' }}>
                      {r.client_name}
                      {r.vip_level === 'vip' && (
                        <span style={{ marginLeft: '8px', background: '#2a2200', color: '#f0c040', fontSize: '10px', padding: '1px 6px', borderRadius: '3px', letterSpacing: '0.1em' }}>VIP</span>
                      )}
                      {r.special_flag && (
                        <span style={{ marginLeft: '6px', color: '#d97706', fontSize: '12px' }}>●</span>
                      )}
                    </div>
                    <div style={{ color: '#555', fontSize: '12px' }}>{r.phone}</div>
                  </div>
                  <span style={{ color: '#ccc', fontSize: '15px', alignSelf: 'center' }}>{r.time}</span>
                  <span style={{ color: '#ccc', fontSize: '15px', alignSelf: 'center' }}>{r.pax}</span>
                  <span style={{ color: r.table_name ? '#ccc' : '#444', fontSize: '14px', alignSelf: 'center' }}>
                    {r.requested_cava ? 'Cava' : (r.table_name ?? '—')}
                  </span>
                  <span style={{ color: r.event_type === 'normal' ? '#444' : '#ccc', fontSize: '13px', textTransform: 'capitalize', alignSelf: 'center' }}>
                    {r.event_type === 'normal' ? '—' : r.event_type}
                  </span>
                  <div style={{ alignSelf: 'center' }}>
                    <span style={{
                      background: s.bg, color: s.color,
                      fontSize: '11px', fontWeight: 500, padding: '3px 10px', borderRadius: '20px',
                      display: 'inline-flex', alignItems: 'center', gap: '5px',
                    }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
                      {s.label}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>

      {/* ── PANEL LATERAL ── */}
      {selected && (
        <aside style={{
          width: '320px', flexShrink: 0, background: '#0f0f0f',
          borderLeft: '1px solid #222', padding: '28px 24px',
          display: 'flex', flexDirection: 'column', overflowY: 'auto',
        }}>

          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
            <div>
              <p style={{ color: '#555', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '4px' }}>
                Reserva #{selected.id}
              </p>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', color: '#fff', fontWeight: 300 }}>
                {selected.client_name}
              </h3>
            </div>
            <button onClick={closePanel}
              style={{ background: '#1a1a1a', border: 'none', color: '#666', width: '28px', height: '28px', borderRadius: '50%', cursor: 'pointer', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={e => (e.currentTarget.style.color = '#666')}>
              ✕
            </button>
          </div>

          {/* Badge estado */}
          {(() => {
            const s = STATUS[selected.status] ?? STATUS.cancelled
            return (
              <div style={{ marginBottom: '20px' }}>
                <span style={{ background: s.bg, color: s.color, fontSize: '12px', fontWeight: 500, padding: '4px 12px', borderRadius: '20px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: s.dot }} />
                  {s.label}
                </span>
              </div>
            )
          })()}

          {/* Datos */}
          <div style={{ background: '#141414', border: '1px solid #222', borderRadius: '8px', marginBottom: '16px', overflow: 'hidden' }}>
            {[
              { label: 'Teléfono', value: selected.phone },
              { label: 'Fecha',    value: new Date(selected.date + 'T12:00:00').toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'long' }) },
              { label: 'Hora',     value: selected.time },
              { label: 'Personas', value: `${selected.pax} personas` },
              { label: 'Mesa',     value: selected.requested_cava ? 'Cava (solicitada)' : (selected.table_name ?? 'Sin asignar') },
              { label: 'Ocasión',  value: selected.event_type === 'normal' ? 'Normal' : selected.event_type },
              { label: 'Nivel',    value: selected.vip_level },
            ].map((row, i, arr) => (
              <div key={row.label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 14px',
                borderBottom: i < arr.length - 1 ? '1px solid #1a1a1a' : 'none',
              }}>
                <span style={{ color: '#555', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>{row.label}</span>
                <span style={{ color: '#ddd', fontSize: '13px', textTransform: 'capitalize', textAlign: 'right', maxWidth: '180px' }}>{row.value}</span>
              </div>
            ))}
          </div>

          {/* Nota cliente */}
          {selected.notes && (
            <div style={{ background: '#141414', border: '1px solid #222', borderRadius: '8px', padding: '12px 14px', marginBottom: '16px' }}>
              <p style={{ color: '#555', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '6px' }}>Nota del cliente</p>
              <p style={{ color: '#bbb', fontSize: '13px', lineHeight: 1.5 }}>{selected.notes}</p>
            </div>
          )}

          {/* Nota interna */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', color: '#555', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '8px' }}>
              Nota interna
            </label>
            <textarea value={adminNote} onChange={e => setAdminNote(e.target.value)}
              placeholder="Agregar nota para el equipo..." rows={3}
              style={{ width: '100%', background: '#141414', border: '1px solid #333', color: '#ddd', padding: '10px 12px', fontSize: '13px', outline: 'none', resize: 'vertical', fontFamily: 'var(--font-body)', lineHeight: 1.5, borderRadius: '6px', transition: 'border-color 0.2s' }}
              onFocus={e => (e.target.style.borderColor = '#555')}
              onBlur={e  => (e.target.style.borderColor = '#333')} />
          </div>

          {/* Acciones */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {(ACTIONS[selected.status] ?? []).map(action => (
              <button key={action.status} disabled={updating}
                onClick={() => action.status === 'cancelled' ? cancelReservation() : changeStatus(action.status)}
                style={{
                  background: action.primary ? '#fff' : '#1a1a1a',
                  color:      action.primary ? '#0a0a0a' : '#888',
                  border:     action.primary ? 'none' : '1px solid #333',
                  padding: '12px', fontSize: '13px', fontWeight: action.primary ? 500 : 400,
                  borderRadius: '6px', cursor: updating ? 'not-allowed' : 'pointer',
                  fontFamily: 'var(--font-body)', transition: 'opacity 0.2s',
                  opacity: updating ? 0.5 : 1,
                }}>
                {updating ? 'Actualizando...' : action.label}
              </button>
            ))}
          </div>

          {/* Feedback */}
          {updateMsg && (
            <div style={{
              marginTop: '14px', padding: '10px 14px', borderRadius: '6px',
              background: updateMsg.ok ? '#0f2010' : '#200f0f',
              border: `1px solid ${updateMsg.ok ? '#1a4020' : '#401a1a'}`,
            }}>
              <p style={{ color: updateMsg.ok ? '#4ade80' : '#f87171', fontSize: '13px' }}>
                {updateMsg.text}
              </p>
            </div>
          )}
        </aside>
      )}
    </div>
  )
}