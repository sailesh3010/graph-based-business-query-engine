function NodeDetail({ node, onClose }) {
  if (!node) return null

  // Fields to skip in the display
  const SKIP_FIELDS = new Set([
    'id', 'color', 'size', 'x', 'y', 'vx', 'vy', 'fx', 'fy',
    'index', '__indexColor', 'neighbor_ids',
  ])

  const entries = Object.entries(node).filter(
    ([key]) => !SKIP_FIELDS.has(key) && key !== 'connections'
  )

  const formatKey = (key) => {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
  }

  const formatValue = (value) => {
    if (value === null || value === undefined || value === '') return '—'
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    return String(value)
  }

  return (
    <>
      <div className="node-detail-header">
        <div>
          <div className="node-detail-title">{node.label || node.id}</div>
          <div className="node-detail-entity">
            Entity: {node.entity || 'Unknown'}
          </div>
        </div>
        <button className="node-detail-close" onClick={onClose}>×</button>
      </div>
      <div className="node-detail-body">
        {entries.map(([key, value]) => (
          <div className="node-detail-row" key={key}>
            <span className="node-detail-key">{formatKey(key)}</span>
            <span className="node-detail-value">{formatValue(value)}</span>
          </div>
        ))}
        {node.connections !== undefined && (
          <div className="node-detail-connections">
            Connections: {node.connections}
          </div>
        )}
      </div>
    </>
  )
}

export default NodeDetail
