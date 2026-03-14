'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const router = useRouter()

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      if (!res.ok) { setError('Usuario o contraseña incorrectos'); return }
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      router.push('/dashboard')
    } catch {
      setError('No se pudo conectar con el servidor')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'transparent',
    border: 'none',
    borderBottom: '1px solid #2a2a2a',
    color: '#f0ebe0',
    padding: '12px 0',
    fontSize: '14px',
    letterSpacing: '0.05em',
    outline: 'none',
    fontFamily: 'var(--font-body)',
    transition: 'border-color 0.2s',
  }

  return (
    <main style={{ display: 'flex', minHeight: '100vh', background: '#080808' }}>

      {/* ── LADO IZQUIERDO — Foto ── */}
      <div style={{
        flex: 1,
        position: 'relative',
        overflow: 'hidden',
        display: 'none',  // oculto en mobile
      }}
        className="photo-panel"
      >
        <Image
          src="/jamon.jpg"
          alt="Jamonería Miguel Martín"
          fill
          style={{ objectFit: 'cover', objectPosition: 'center' }}
          priority
        />
        {/* Overlay oscuro sobre la foto */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(to right, rgba(8,8,8,0) 70%, #080808 100%)',
        }} />
               {/* Gradiente inferior para legibilidad */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(to top, rgba(8,8,8,0.75) 0%, rgba(8,8,8,0) 35%), linear-gradient(to right, rgba(8,8,8,0) 85%, #080808 100%)',
        }} />

        {/* Texto sobre la foto */}
        <div style={{
          position: 'absolute',
          bottom: '90px',
          left: '100px',
        }}>
          <p style={{
            color: 'rgba(255, 255, 255, 0.6)',
            fontSize: '12px',
            letterSpacing: '0.4em',
            textTransform: 'uppercase',
            marginBottom: '8px',
          }}>
            Calle Noruega 1382, San Juan
          </p>
          <h2 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '42px',
            color: '#f0ebe0',
            fontWeight: 300,
            lineHeight: 1.1,
            textShadow: '0 2px 20px rgba(0,0,0,0.5)',
          }}>
            Miguel Martín<br />Jamonería
          </h2>
        </div>
          <p style={{
            color: 'rgba(240,235,224,0.4)',
            fontSize: '10px',
            letterSpacing: '0.4em',
            textTransform: 'uppercase',
            marginBottom: '8px',
          }}>
            Calle Noruega 1382, San Juan
          </p>
          <h2 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '42px',
            color: '#f0ebe0',
            fontWeight: 300,
            lineHeight: 1.1,
          }}>
            Miguel Martín<br />Jamonería
          </h2>
        </div>

      {/* ── LADO DERECHO — Login ── */}
      <div style={{
        width: '420px',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '60px 56px',
        borderLeft: '1px solid #1a1a1a',
      }}>

        {/* Logo */}
        <div style={{ marginBottom: '56px', textAlign: 'center' }}>
          <Image
            src="/logo.png"
            alt="MM"
            width={180}
            height={180}
            style={{ borderRadius: '10px' }}
            priority
          />
        </div>

        {/* Título */}
        <div style={{ width: '100%', marginBottom: '40px' }}>
          <p style={{
            color: '#6a6560',
            fontSize: '13px',
            letterSpacing: '0.35em',
            textTransform: 'uppercase',
            marginBottom: '6px',
          }}>
            Panel de gestión
          </p>
          <h1 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '35px',
            color: '#f0ebe0',
            fontWeight: 300,
            lineHeight: 1,
          }}>
            Iniciar sesión
          </h1>
        </div>

        {/* Formulario */}
        <form onSubmit={handleLogin} style={{ width: '100%' }}>

          <div style={{ marginBottom: '28px' }}>
            <label style={{
              display: 'block',
              color: '#6a6560',
              fontSize: '9px',
              letterSpacing: '0.35em',
              textTransform: 'uppercase',
              marginBottom: '10px',
            }}>
              Usuario
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoComplete="username"
              style={inputStyle}
              onFocus={e => (e.target.style.borderBottomColor = '#e8e3dc')}
              onBlur={e  => (e.target.style.borderBottomColor = '#2a2a2a')}
            />
          </div>

          <div style={{ marginBottom: '36px' }}>
            <label style={{
              display: 'block',
              color: '#6a6560',
              fontSize: '9px',
              letterSpacing: '0.35em',
              textTransform: 'uppercase',
              marginBottom: '10px',
            }}>
              Contraseña
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={inputStyle}
              onFocus={e => (e.target.style.borderBottomColor = '#e8e3dc')}
              onBlur={e  => (e.target.style.borderBottomColor = '#2a2a2a')}
            />
          </div>

          {error && (
            <p style={{
              color: '#805050',
              fontSize: '12px',
              letterSpacing: '0.05em',
              marginBottom: '20px',
              marginTop: '-20px',
            }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              background: '#f0ebe0',
              color: '#080808',
              border: 'none',
              padding: '15px',
              fontSize: '10px',
              letterSpacing: '0.35em',
              textTransform: 'uppercase',
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.5 : 1,
              transition: 'opacity 0.2s, background 0.2s',
              fontFamily: 'var(--font-body)',
            }}
            onMouseEnter={e => { if (!loading) e.currentTarget.style.background = '#e8e3dc' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#f0ebe0' }}
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
      </div>

      {/* CSS para mostrar la foto en desktop */}
      <style>{`
        @media (min-width: 768px) {
          .photo-panel { display: block !important; }
        }
      `}</style>

    </main>
  )
}