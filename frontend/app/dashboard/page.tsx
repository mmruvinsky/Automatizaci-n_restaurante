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

const STATUS: Record<string, { label: string; color: string; bg: string }> = {
  confirmed: { label: 'Confirmada', color: '#f0ebe0', bg: 'rgba(240,235,224,0.12)' },
  pending:   { label: 'Pendiente',  color: '#c8c0b8', bg: 'rgba(200,192,184,0.12)' },
  cancelled: { label: 'Cancelada',  color: '#6a6560', bg: 'rgba(106,101,96,0.15)'  },
  completed: { label: 'Completada', color: '#9a9590', bg: 'rgba(154,149,144,0.15)' },
}

const FILTERS = [
  { value: 'all',       label: 'Todas'       },
  { value: 'confirmed', label: 'Confirmadas' },
  { value: 'pending',   label: 'Pendientes'  },
  { value: 'cancelled', label: 'Canceladas'  },
]

const ACTIONS: Record<string, { status: string; label: string; color: string; bg: string }[]> = {
  pending: [
    { status: 'confirmed', label: 'Confirmar',  color: '#080808', bg: '#f0ebe0'      },
    { status: 'cancelled', label: 'Cancelar',   color: '#f0ebe0', bg: 'transparent'  },
  ],
  confirmed: [
    { status: 'completed', label: 'Completada', color: '#080808', bg: '#f0ebe0'      },
    { status: 'cancelled', label: 'Cancelar',   color: '#f0ebe0', bg: 'transparent'  },
  ],
  cancelled: [
    { status: 'pending',   label: 'Reactivar',  color: '#080808', bg: '#f0ebe0'      },
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
  const [updateMsg, setUpdateMsg]       = useState('')

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
    } catch { /* backend offline */ }
    finally  { setLoading(false) }
  }

  function openPanel(r: Reservation) {
    setSelected(r)
    setAdminNote(r.admin_notes ?? '')
    setUpdateMsg('')
  }

  function closePanel() {
    setSelected(null)
    setAdminNote('')
    setUpdateMsg('')
  }

  async function changeStatus(newStatus: string) {
    if (!selected) return
    setUpdating(true)
    setUpdateMsg('')
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`http://localhost:8000/reservations/${selected.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status: newStatus, admin_notes: adminNote || undefined })
      })
      if (res.ok) {
        setUpdateMsg('✓ Actualizado correctamente')
        setReservations(prev => prev.map(r =>
          r.id === selected.id
            ? { ...r, status: newStatus as Reservation['status'], admin_notes: adminNote }
            : r
        ))
        setSelected(prev => prev ? { ...prev, status: newStatus as Reservation['status'] } : null)
      } else {
        const err = await res.json()
        setUpdateMsg(`✗ Error: ${err.detail ?? 'Algo salió mal'}`)
      }
    } catch {
      setUpdateMsg('✗ No se pudo conectar con el servidor')
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
        setUpdateMsg('✓ Reserva cancelada')
        setReservations(prev => prev.map(r =>
          r.id === selected.id ? { ...r, status: 'cancelled' } : r
        ))
        setSelected(prev => prev ? { ...prev, status: 'cancelled' } : null)
      }
    } catch {
      setUpdateMsg('✗ Error al cancelar')
    } finally {
      setUpdating(false)
    }
  }

  function logout() {
    localStorage.removeItem('token')
    router.push('/')
  }

  const visible = filter === 'all'
    ? reservations
    : reservations.filter(r => r.status === filter)

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
    <div style={{ display: 'flex', minHeight: '100vh', background: '#080808' }}>

      {/* ── SIDEBAR ── */}
      <aside style={{
        width: '210px', background: '#0a0a0a', borderRight: '1px solid #1e1e1e',
        padding: '32px 20px', display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        <div style={{ marginBottom: '40px', textAlign: 'center' }}>
          <Image src="/logo.png" alt="MM Jamonería" width={100} height={100} style={{ borderRadius: '3px' }} />
        </div>
        <nav style={{ flex: 1 }}>
          <div style={{ color: '#f0ebe0', fontSize: '12px', letterSpacing: '0.2em', textTransform: 'uppercase', padding: '14px 0', borderBottom: '1px solid #2a2a2a', cursor: 'pointer' }}>
            Reservas
          </div>
          <div style={{ color: '#5a5550', fontSize: '12px', letterSpacing: '0.2em', textTransform: 'uppercase', padding: '14px 0', borderBottom: '1px solid #1e1e1e', cursor: 'not-allowed' }}>
            Mesas
          </div>
        </nav>
        <button onClick={logout}
          style={{ background: 'none', border: '1px solid #3a3530', color: '#7a7570', padding: '12px', fontSize: '11px', letterSpacing: '0.2em', textTransform: 'uppercase', cursor: 'pointer', fontFamily: 'var(--font-body)', transition: 'all 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = '#f0ebe0'; e.currentTarget.style.color = '#f0ebe0' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = '#3a3530'; e.currentTarget.style.color = '#7a7570' }}>
          Cerrar sesión
        </button>
      </aside>

      {/* ── MAIN ── */}
      <main style={{ flex: 1, padding: '40px 48px', overflowY: 'auto', minWidth: 0 }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '40px' }}>
          <div>
            <p style={{ color: '#8a8580', fontSize: '11px', letterSpacing: '0.3em', textTransform: 'uppercase', marginBottom: '8px' }}>
              Reservas del día
            </p>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '44px', color: '#f0ebe0', fontWeight: 300, textTransform: 'capitalize', lineHeight: 1 }}>
              {dateLabel}
            </h2>
          </div>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            style={{ background: '#111', border: '1px solid #3a3530', color: '#f0ebe0', padding: '12px 16px', fontSize: '14px', outline: 'none', fontFamily: 'var(--font-body)', cursor: 'pointer' }}
            onFocus={e => (e.target.style.borderColor = '#e8e3dc')}
            onBlur={e  => (e.target.style.borderColor = '#3a3530')} />
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '40px' }}>
          {[
            { label: 'Total reservas',      value: stats.total     },
            { label: 'Confirmadas',         value: stats.confirmed },
            { label: 'Pendientes',          value: stats.pending   },
            { label: 'Cubiertos esperados', value: stats.pax       },
          ].map(s => (
            <div key={s.label} style={{ background: '#111', border: '1px solid #2a2a2a', padding: '20px 24px' }}>
              <p style={{ color: '#9a9590', fontSize: '11px', letterSpacing: '0.25em', textTransform: 'uppercase', marginBottom: '12px' }}>
                {s.label}
              </p>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '48px', color: '#f0ebe0', fontWeight: 300, lineHeight: 1 }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Filtros */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '28px' }}>
          {FILTERS.map(f => (
            <button key={f.value} onClick={() => setFilter(f.value)} style={{
              background:  filter === f.value ? '#f0ebe0' : 'transparent',
              color:       filter === f.value ? '#080808' : '#9a9590',
              border: '1px solid', borderColor: filter === f.value ? '#f0ebe0' : '#3a3530',
              padding: '9px 20px', fontSize: '11px', letterSpacing: '0.2em',
              textTransform: 'uppercase', cursor: 'pointer', fontFamily: 'var(--font-body)', transition: 'all 0.15s',
            }}
              onMouseEnter={e => { if (filter !== f.value) { e.currentTarget.style.borderColor = '#9a9590'; e.currentTarget.style.color = '#f0ebe0' }}}
              onMouseLeave={e => { if (filter !== f.value) { e.currentTarget.style.borderColor = '#3a3530'; e.currentTarget.style.color = '#9a9590' }}}>
              {f.label}
            </button>
          ))}
        </div>

        {/* Tabla */}
        {loading ? (
          <p style={{ color: '#7a7570', fontSize: '14px', paddingTop: '60px' }}>Cargando reservas...</p>
        ) : visible.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '32px', color: '#3a3530', fontWeight: 300 }}>
              Sin reservas para este día
            </p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Cliente', 'Hora', 'Pax', 'Mesa', 'Ocasión', 'Estado'].map(col => (
                  <th key={col} style={{ color: '#9a9590', fontSize: '11px', letterSpacing: '0.25em', textTransform: 'uppercase', textAlign: 'left', padding: '0 20px 16px 0', fontWeight: 400, borderBottom: '1px solid #2a2a2a' }}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map(r => {
                const s = STATUS[r.status] ?? STATUS.cancelled
                const isSelected = selected?.id === r.id
                return (
                  <tr key={r.id} onClick={() => openPanel(r)}
                    style={{
                      borderBottom: '1px solid #161616', cursor: 'pointer', transition: 'background 0.15s',
                      background: isSelected ? '#111' : 'transparent',
                      borderLeft: isSelected ? '2px solid #f0ebe0' : '2px solid transparent',
                    }}
                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#0f0f0f' }}
                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}>

                    <td style={{ padding: '18px 20px 18px 8px' }}>
                      <div style={{ color: '#f0ebe0', fontSize: '15px', marginBottom: '4px' }}>
                        {r.client_name}
                        {r.vip_level === 'vip' && (
                          <span style={{ marginLeft: '8px', color: '#9a9590', fontSize: '10px', letterSpacing: '0.2em' }}>VIP</span>
                        )}
                        {r.special_flag && (
                          <span style={{ marginLeft: '6px', color: '#9a9590', fontSize: '11px' }}>●</span>
                        )}
                      </div>
                      <div style={{ color: '#7a7570', fontSize: '13px' }}>{r.phone}</div>
                    </td>
                    <td style={{ padding: '18px 20px 18px 0', color: '#f0ebe0', fontSize: '15px' }}>{r.time}</td>
                    <td style={{ padding: '18px 20px 18px 0', color: '#f0ebe0', fontSize: '15px' }}>{r.pax}</td>
                    <td style={{ padding: '18px 20px 18px 0', fontSize: '14px' }}>
                      {r.requested_cava
                        ? <span style={{ color: '#c8c0b8' }}>Cava</span>
                        : <span style={{ color: r.table_name ? '#f0ebe0' : '#5a5550' }}>{r.table_name ?? '—'}</span>}
                    </td>
                    <td style={{ padding: '18px 20px 18px 0', color: '#8a8580', fontSize: '14px', textTransform: 'capitalize' }}>
                      {r.event_type === 'normal' ? '—' : r.event_type}
                    </td>
                    <td style={{ padding: '18px 20px 18px 0' }}>
                      <span style={{ background: s.bg, color: s.color, fontSize: '10px', letterSpacing: '0.15em', textTransform: 'uppercase', padding: '5px 12px', border: '1px solid rgba(255,255,255,0.06)' }}>
                        {s.label}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </main>

      {/* ── PANEL LATERAL DE DETALLE ── */}
      {selected && (
        <aside style={{
          width: '340px', flexShrink: 0, background: '#0a0a0a',
          borderLeft: '1px solid #1e1e1e', padding: '32px 28px',
          display: 'flex', flexDirection: 'column', overflowY: 'auto',
        }}>

          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' }}>
            <div>
              <p style={{ color: '#8a8580', fontSize: '10px', letterSpacing: '0.3em', textTransform: 'uppercase', marginBottom: '6px' }}>
                Reserva #{selected.id}
              </p>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', color: '#f0ebe0', fontWeight: 300, lineHeight: 1.1 }}>
                {selected.client_name}
              </h3>
            </div>
            <button onClick={closePanel}
              style={{ background: 'none', border: 'none', color: '#5a5550', fontSize: '20px', cursor: 'pointer', padding: '4px', lineHeight: 1 }}
              onMouseEnter={e => (e.currentTarget.style.color = '#f0ebe0')}
              onMouseLeave={e => (e.currentTarget.style.color = '#5a5550')}>
              ✕
            </button>
          </div>

          {/* Estado badge */}
          <div style={{ marginBottom: '28px' }}>
            {(() => {
              const s = STATUS[selected.status] ?? STATUS.cancelled
              return (
                <span style={{ background: s.bg, color: s.color, fontSize: '10px', letterSpacing: '0.2em', textTransform: 'uppercase', padding: '6px 14px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  {s.label}
                </span>
              )
            })()}
          </div>

          {/* Datos de la reserva */}
          <div style={{ borderTop: '1px solid #1e1e1e', paddingTop: '20px', marginBottom: '24px' }}>
            {[
              { label: 'Teléfono', value: selected.phone },
              { label: 'Fecha',    value: new Date(selected.date + 'T12:00:00').toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' }) },
              { label: 'Hora',     value: selected.time },
              { label: 'Personas', value: `${selected.pax} pax` },
              { label: 'Mesa',     value: selected.requested_cava ? 'Cava (solicitada)' : (selected.table_name ?? 'Sin asignar') },
              { label: 'Ocasión',  value: selected.event_type === 'normal' ? 'Normal' : selected.event_type },
              { label: 'Nivel',    value: selected.vip_level.toUpperCase() },
            ].map(row => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #161616', gap: '12px' }}>
                <span style={{ color: '#7a7570', fontSize: '12px', letterSpacing: '0.1em', textTransform: 'uppercase', flexShrink: 0 }}>{row.label}</span>
                <span style={{ color: '#f0ebe0', fontSize: '13px', textAlign: 'right', textTransform: 'capitalize' }}>{row.value}</span>
              </div>
            ))}
          </div>

          {/* Nota del cliente */}
          {selected.notes && (
            <div style={{ background: '#111', border: '1px solid #1e1e1e', padding: '14px 16px', marginBottom: '24px' }}>
              <p style={{ color: '#7a7570', fontSize: '10px', letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '6px' }}>Nota del cliente</p>
              <p style={{ color: '#c8c0b8', fontSize: '13px', lineHeight: 1.5 }}>{selected.notes}</p>
            </div>
          )}

          {/* Nota interna */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', color: '#7a7570', fontSize: '10px', letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '10px' }}>
              Nota interna
            </label>
            <textarea value={adminNote} onChange={e => setAdminNote(e.target.value)}
              placeholder="Agregar nota para el equipo..." rows={3}
              style={{ width: '100%', background: '#111', border: '1px solid #2a2a2a', color: '#f0ebe0', padding: '12px 14px', fontSize: '13px', outline: 'none', resize: 'vertical', fontFamily: 'var(--font-body)', lineHeight: 1.5, transition: 'border-color 0.2s' }}
              onFocus={e => (e.target.style.borderColor = '#e8e3dc')}
              onBlur={e  => (e.target.style.borderColor = '#2a2a2a')} />
          </div>

          {/* Botones de acción */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {(ACTIONS[selected.status] ?? []).map(action => (
              <button key={action.status} disabled={updating}
                onClick={() => action.status === 'cancelled' ? cancelReservation() : changeStatus(action.status)}
                style={{
                  background: action.bg, color: action.color,
                  border: action.bg === 'transparent' ? '1px solid #3a3530' : 'none',
                  padding: '13px', fontSize: '11px', letterSpacing: '0.25em',
                  textTransform: 'uppercase', cursor: updating ? 'not-allowed' : 'pointer',
                  fontFamily: 'var(--font-body)', transition: 'opacity 0.2s',
                  opacity: updating ? 0.5 : 1,
                }}
                onMouseEnter={e => { if (!updating) e.currentTarget.style.opacity = '0.8' }}
                onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}>
                {updating ? 'Actualizando...' : action.label}
              </button>
            ))}
          </div>

          {/* Feedback */}
          {updateMsg && (
            <p style={{ marginTop: '16px', fontSize: '13px', letterSpacing: '0.05em', color: updateMsg.startsWith('✓') ? '#7aaa7a' : '#aa6a6a' }}>
              {updateMsg}
            </p>
          )}

        </aside>
      )}
    </div>
  )
}