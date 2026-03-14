'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

type Table = {
  id: number
  name: string
  capacity: number
  type: 'standard' | 'cava'
  is_active: boolean
}

type Reservation = {
  id: number
  client_name: string
  phone: string
  time: string
  pax: number
  status: string
  table_name: string | null
  event_type: string
  vip_level: string
}

type PhysicalTable = {
  baseNumber: number
  capacity: number
  type: 'standard' | 'cava'
  isBar: boolean
  isMeson: boolean
  slot1: { table: Table; reservation: Reservation | null } | null
  slot2: { table: Table; reservation: Reservation | null } | null
}

type Section = 'salon' | 'cava' | 'afuera'

const BARS  = [9, 10, 14, 15]
const MESON = [8]

function getBase(name: string): number | null {
  const m = name.match(/\d+/)
  if (!m) return null
  const n = parseInt(m[0])
  return n > 100 ? n - 100 : n
}

function getSection(base: number): Section {
  if (base === 11) return 'cava'
  if (base >= 1 && base <= 10) return 'salon'
  return 'afuera'
}

function slotStyle(res: Reservation | null) {
  if (!res || res.status === 'cancelled') {
    return { bg: '#111', border: '#1e1e1e', label: '#333', nameColor: '#333' }
  }
  if (res.status === 'confirmed') {
    return { bg: '#0d1f0f', border: '#1a4020', label: '#4ade80', nameColor: '#fff' }
  }
  return { bg: '#1a1200', border: '#3a2800', label: '#f0a020', nameColor: '#fff' }
}

export default function MesasPage() {
  const router = useRouter()
  const [tables, setTables]         = useState<Table[]>([])
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [loading, setLoading]       = useState(true)
  const [date, setDate]             = useState(() => new Date().toISOString().split('T')[0])
  const [section, setSection]       = useState<Section>('salon')
  const [selected, setSelected]     = useState<PhysicalTable | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { router.push('/'); return }
    fetchData(token)
  }, [date])

  async function fetchData(token?: string) {
    setLoading(true)
    const t = token || localStorage.getItem('token') || ''
    try {
      const [tRes, rRes] = await Promise.all([
        fetch('http://localhost:8000/tables/?only_active=true', { headers: { Authorization: `Bearer ${t}` } }),
        fetch(`http://localhost:8000/reservations/?date=${date}`, { headers: { Authorization: `Bearer ${t}` } }),
      ])
      if (tRes.status === 401) { router.push('/'); return }
      setTables(await tRes.json())
      setReservations(await rRes.json())
    } catch { /* offline */ }
    finally  { setLoading(false) }
  }

  function logout() {
    localStorage.removeItem('token')
    router.push('/')
  }

  const physicalTables: PhysicalTable[] = (() => {
    const map = new Map<number, PhysicalTable>()
    tables.forEach(table => {
      const base = getBase(table.name)
      if (base === null) return
      const numStr = table.name.match(/\d+/)
      const num = numStr ? parseInt(numStr[0]) : 0
      const isSecond = num > 100
      const res = reservations.find(r => r.table_name === table.name && r.status !== 'cancelled') ?? null
      if (!map.has(base)) {
        map.set(base, {
          baseNumber: base, capacity: table.capacity, type: table.type,
          isBar: BARS.includes(base), isMeson: MESON.includes(base),
          slot1: null, slot2: null,
        })
      }
      const p = map.get(base)!
      if (isSecond) p.slot2 = { table, reservation: res }
      else          p.slot1 = { table, reservation: res }
    })
    return Array.from(map.values()).sort((a, b) => a.baseNumber - b.baseNumber)
  })()

  const sectionTables = physicalTables.filter(t => getSection(t.baseNumber) === section)

  const stats = {
    total:    physicalTables.length,
    free1:    physicalTables.filter(t => !t.slot1?.reservation).length,
    free2:    physicalTables.filter(t => !t.slot2?.reservation).length,
    occupied: physicalTables.filter(t => t.slot1?.reservation && t.slot2?.reservation).length,
  }

  const dateLabel = new Date(date + 'T12:00:00').toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long'
  })

  const SECTION_LABELS: Record<Section, string> = { salon: 'Salón', cava: 'Cava', afuera: 'Afuera' }

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
          <div onClick={() => router.push('/dashboard')}
            style={{ color: '#666', fontSize: '13px', padding: '10px 14px', borderRadius: '6px', cursor: 'pointer', transition: 'all 0.15s' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#1a1a1a'; e.currentTarget.style.color = '#fff' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#666' }}>
            Reservas
          </div>
          <div style={{ background: '#1a1a1a', color: '#fff', fontSize: '13px', fontWeight: 500, padding: '10px 14px', borderRadius: '6px', cursor: 'pointer' }}>
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
              Estado de mesas
            </p>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '36px', color: '#fff', fontWeight: 300, textTransform: 'capitalize' }}>
              {dateLabel}
            </h2>
          </div>
          <input type="date" value={date} onChange={e => { setDate(e.target.value); setSelected(null) }}
            style={{ background: '#1a1a1a', border: '1px solid #333', color: '#fff', padding: '10px 14px', fontSize: '14px', outline: 'none', borderRadius: '6px', fontFamily: 'var(--font-body)', cursor: 'pointer' }}
            onFocus={e => (e.target.style.borderColor = '#555')}
            onBlur={e  => (e.target.style.borderColor = '#333')} />
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px', marginBottom: '28px' }}>
          {[
            { label: 'Mesas físicas',    value: stats.total,    accent: '#fff'    },
            { label: 'Libres turno 1',   value: stats.free1,    accent: '#4ade80' },
            { label: 'Libres turno 2',   value: stats.free2,    accent: '#4ade80' },
            { label: 'Ocupadas ambas',   value: stats.occupied, accent: '#f87171' },
          ].map(s => (
            <div key={s.label} style={{ background: '#141414', border: '1px solid #222', padding: '16px 20px', borderRadius: '8px' }}>
              <p style={{ color: '#555', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '8px' }}>
                {s.label}
              </p>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '40px', color: s.accent, fontWeight: 300, lineHeight: 1 }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Tabs sección */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '20px' }}>
          {(['salon', 'afuera', 'cava'] as Section[]).map(s => (
            <button key={s} onClick={() => { setSection(s); setSelected(null) }}
              style={{
                background: section === s ? '#fff' : '#141414',
                color:      section === s ? '#0a0a0a' : '#888',
                border:     `1px solid ${section === s ? '#fff' : '#333'}`,
                padding: '7px 20px', fontSize: '12px', fontWeight: section === s ? 500 : 400,
                borderRadius: '5px', cursor: 'pointer', fontFamily: 'var(--font-body)', transition: 'all 0.15s',
              }}>
              {SECTION_LABELS[s]}
            </button>
          ))}

          {/* Leyenda */}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '16px', alignItems: 'center' }}>
            {[
              { color: '#333', label: 'Libre'      },
              { color: '#4ade80', label: 'Confirmado' },
              { color: '#f0a020', label: 'Pendiente'  },
            ].map(l => (
              <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: l.color }} />
                <span style={{ color: '#555', fontSize: '12px' }}>{l.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Header columnas */}
        {!loading && sectionTables.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr 1fr', gap: '8px', marginBottom: '6px' }}>
            <div />
            <p style={{ color: '#444', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Turno 1</p>
            <p style={{ color: '#444', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Turno 2</p>
          </div>
        )}

        {/* Grilla */}
        {loading ? (
          <p style={{ color: '#555', fontSize: '14px', paddingTop: '40px' }}>Cargando mesas...</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {sectionTables.map(table => {
              const isSelected = selected?.baseNumber === table.baseNumber
              const s1 = slotStyle(table.slot1?.reservation ?? null)
              const s2 = slotStyle(table.slot2?.reservation ?? null)
              const label = table.type === 'cava' ? 'Cava' : `Mesa ${table.baseNumber}`

              return (
                <div key={table.baseNumber}
                  onClick={() => setSelected(isSelected ? null : table)}
                  style={{
                    display: 'grid', gridTemplateColumns: '150px 1fr 1fr',
                    gap: '5px', alignItems: 'stretch', cursor: 'pointer',
                    borderLeft: `3px solid ${isSelected ? '#fff' : 'transparent'}`,
                    paddingLeft: isSelected ? '4px' : '0',
                    transition: 'all 0.15s',
                  }}>

                  {/* Nombre */}
                  <div style={{
                    background: '#111', border: '1px solid #1e1e1e',
                    padding: '10px 14px', borderRadius: '6px',
                    display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '58px',
                  }}>
                    <span style={{ color: '#fff', fontSize: '14px', fontWeight: 500 }}>{label}</span>
                    <span style={{ color: '#444', fontSize: '12px', marginTop: '2px' }}>
                      {table.capacity} pax
                      {table.isBar ? ' · barra' : table.isMeson ? ' · mesón' : ''}
                    </span>
                  </div>

                  {/* Slot 1 */}
                  <div style={{ background: s1.bg, border: `1px solid ${s1.border}`, padding: '10px 14px', borderRadius: '6px', minHeight: '58px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    {table.slot1?.reservation ? (
                      <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ color: s1.nameColor, fontSize: '14px', fontWeight: 500 }}>{table.slot1.reservation.client_name}</span>
                          <span style={{ color: s1.label, fontSize: '11px', fontWeight: 600 }}>● {table.slot1.reservation.status}</span>
                        </div>
                        <span style={{ color: '#666', fontSize: '12px', marginTop: '2px' }}>
                          {table.slot1.reservation.time} · {table.slot1.reservation.pax} pax
                        </span>
                      </>
                    ) : (
                      <span style={{ color: '#2a2a2a', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Libre</span>
                    )}
                  </div>

                  {/* Slot 2 */}
                  <div style={{ background: s2.bg, border: `1px solid ${s2.border}`, padding: '10px 14px', borderRadius: '6px', minHeight: '58px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    {table.slot2?.reservation ? (
                      <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ color: s2.nameColor, fontSize: '14px', fontWeight: 500 }}>{table.slot2.reservation.client_name}</span>
                          <span style={{ color: s2.label, fontSize: '11px', fontWeight: 600 }}>● {table.slot2.reservation.status}</span>
                        </div>
                        <span style={{ color: '#666', fontSize: '12px', marginTop: '2px' }}>
                          {table.slot2.reservation.time} · {table.slot2.reservation.pax} pax
                        </span>
                      </>
                    ) : (
                      <span style={{ color: '#2a2a2a', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Libre</span>
                    )}
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
          width: '280px', flexShrink: 0, background: '#0f0f0f',
          borderLeft: '1px solid #222', padding: '28px 22px',
          display: 'flex', flexDirection: 'column', overflowY: 'auto',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
            <div>
              <p style={{ color: '#555', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '4px' }}>
                {selected.type === 'cava' ? 'Cava' : selected.isBar ? 'Barra' : selected.isMeson ? 'Mesón' : 'Mesa'}
              </p>
              <h3 style={{ color: '#fff', fontSize: '22px', fontFamily: 'var(--font-display)', fontWeight: 300 }}>
                {selected.type === 'cava' ? 'Cava' : `Mesa ${selected.baseNumber}`}
              </h3>
              <p style={{ color: '#444', fontSize: '12px', marginTop: '2px' }}>{selected.capacity} personas máx.</p>
            </div>
            <button onClick={() => setSelected(null)}
              style={{ background: '#1a1a1a', border: 'none', color: '#666', width: '28px', height: '28px', borderRadius: '50%', cursor: 'pointer', fontSize: '13px' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={e => (e.currentTarget.style.color = '#666')}>
              ✕
            </button>
          </div>

          <SlotDetail title={`Turno 1 — Mesa ${selected.baseNumber}`} reservation={selected.slot1?.reservation ?? null} />
          <div style={{ height: '16px' }} />
          <SlotDetail title={`Turno 2 — Mesa ${selected.baseNumber + 100}`} reservation={selected.slot2?.reservation ?? null} />
        </aside>
      )}
    </div>
  )
}

function SlotDetail({ title, reservation }: { title: string; reservation: Reservation | null }) {
  const s = slotStyle(reservation)
  return (
    <div>
      <p style={{ color: '#444', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '10px' }}>{title}</p>
      {reservation ? (
        <div style={{ background: s.bg, border: `1px solid ${s.border}`, borderRadius: '8px', padding: '14px' }}>
          <p style={{ color: '#fff', fontSize: '15px', fontWeight: 500, marginBottom: '10px' }}>{reservation.client_name}</p>
          {[
            { label: 'Teléfono', value: reservation.phone },
            { label: 'Hora',     value: reservation.time },
            { label: 'Personas', value: `${reservation.pax} pax` },
            { label: 'Ocasión',  value: reservation.event_type === 'normal' ? '—' : reservation.event_type },
            { label: 'Estado',   value: reservation.status },
          ].map((row, i, arr) => (
            <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
              <span style={{ color: '#555', fontSize: '11px', textTransform: 'uppercase' }}>{row.label}</span>
              <span style={{ color: '#ccc', fontSize: '12px', textTransform: 'capitalize' }}>{row.value}</span>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: '8px', padding: '14px' }}>
          <p style={{ color: '#333', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Libre</p>
        </div>
      )}
    </div>
  )
}