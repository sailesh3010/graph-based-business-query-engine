import { useState, useRef, useEffect } from 'react'

const API_BASE = '/api'

function ChatPanel({ onHighlightNodes }) {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: 'Hi! I can help you analyze the **Order to Cash** process.\n\nAsk me about sales orders, deliveries, billing documents, journal entries, payments, customers, or products.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef()

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
    const query = input.trim()
    if (!query || loading) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: query }])
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const data = await res.json()

      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: data.answer,
          sql: data.sql,
          results: data.results,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: 'Sorry, I encountered an error connecting to the server. Please make sure the backend is running.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-panel">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-title">Chat with Graph</div>
        <div className="chat-header-subtitle">Order to Cash</div>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="chat-message bot">
            <div className="chat-avatar bot">D</div>
            <div className="chat-loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <div className="chat-status">
          <span className="status-dot"></span>
          Dodge AI is awaiting instructions
        </div>
        <div className="chat-input-wrapper">
          <input
            className="chat-input"
            type="text"
            placeholder="Analyze anything"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            className="chat-send-btn"
            onClick={sendMessage}
            disabled={!input.trim() || loading}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }) {
  const [showSql, setShowSql] = useState(false)
  const isBot = message.role === 'bot'

  // Simple markdown-ish rendering
  const renderText = (text) => {
    if (!text) return null
    // Split by double newlines for paragraphs
    const paragraphs = text.split(/\n\n+/)
    return paragraphs.map((para, i) => {
      // Check if it's a list
      const lines = para.split('\n')
      const isList = lines.every(
        (l) => l.trim().startsWith('- ') || l.trim().startsWith('* ') || /^\d+\.\s/.test(l.trim()) || l.trim() === ''
      )

      if (isList) {
        const items = lines.filter((l) => l.trim())
        return (
          <ul key={i} style={{ margin: '6px 0', paddingLeft: '18px' }}>
            {items.map((item, j) => (
              <li key={j} dangerouslySetInnerHTML={{
                __html: formatInline(item.replace(/^[-*]\s+|^\d+\.\s+/, ''))
              }} />
            ))}
          </ul>
        )
      }

      return (
        <p key={i} dangerouslySetInnerHTML={{ __html: formatInline(para) }} />
      )
    })
  }

  const formatInline = (text) => {
    return text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br/>')
  }

  return (
    <div className={`chat-message ${message.role}`}>
      <div className={`chat-avatar ${message.role}`}>
        {isBot ? 'D' : 'Y'}
      </div>
      <div className="chat-bubble">
        {isBot && (
          <>
            <div className="chat-bubble-name">Dodge AI</div>
            <div className="chat-bubble-label">Graph Agent</div>
          </>
        )}
        {renderText(message.text)}

        {/* SQL toggle */}
        {message.sql && (
          <>
            <button
              className="chat-sql-toggle"
              onClick={() => setShowSql(!showSql)}
            >
              {showSql ? '▾ Hide SQL' : '▸ Show SQL'}
            </button>
            {showSql && (
              <div className="chat-sql-block">{message.sql}</div>
            )}
          </>
        )}

        {/* Results table */}
        {message.results && message.results.length > 0 && message.results.length <= 20 && (
          <ResultsTable results={message.results} />
        )}
      </div>
    </div>
  )
}

function ResultsTable({ results }) {
  if (!results || results.length === 0) return null
  const columns = Object.keys(results[0])

  return (
    <div className="results-table-wrapper">
      <table className="results-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col.replace(/_/g, ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col}>{row[col] ?? '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ChatPanel
