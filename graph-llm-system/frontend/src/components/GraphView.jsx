import { useRef, useCallback, useEffect, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import NodeDetail from './NodeDetail'

const ENTITY_COLORS = {
  SalesOrder: '#4A90D9',
  SalesOrderItem: '#6AB0E4',
  Delivery: '#E67E22',
  DeliveryItem: '#F0A04B',
  BillingDocument: '#27AE60',
  BillingDocumentItem: '#58D68D',
  JournalEntry: '#8E44AD',
  Payment: '#E74C3C',
  Customer: '#F39C12',
  Product: '#1ABC9C',
  Plant: '#95A5A6',
}

const ENTITY_SIZES = {
  SalesOrder: 6,
  SalesOrderItem: 3,
  Delivery: 5,
  DeliveryItem: 3,
  BillingDocument: 5,
  BillingDocumentItem: 3,
  JournalEntry: 4,
  Payment: 4,
  Customer: 7,
  Product: 5,
  Plant: 4,
}

function GraphView({
  graphData,
  loading,
  selectedNode,
  graphStats,
  showLabels,
  setShowLabels,
  onNodeClick,
  onCloseDetail,
  highlightNodes,
}) {
  const graphRef = useRef()
  const containerRef = useRef()
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const [detailPos, setDetailPos] = useState(null)

  // Measure container
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({ width: rect.width, height: rect.height })
      }
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  // Zoom to fit on data load
  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0) {
      setTimeout(() => {
        graphRef.current.zoomToFit(400, 50)
      }, 500)
    }
  }, [graphData.nodes.length])

  const handleNodeClick = useCallback((node, event) => {
    // Position detail popover near the click
    const rect = containerRef.current.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    // Adjust so popover stays in view
    const popX = Math.min(x + 10, dimensions.width - 340)
    const popY = Math.min(y - 20, dimensions.height - 440)

    setDetailPos({ x: Math.max(10, popX), y: Math.max(10, popY) })
    onNodeClick(node.id)
  }, [onNodeClick, dimensions])

  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const entity = node.entity || 'Unknown'
    const color = ENTITY_COLORS[entity] || '#ccc'
    const size = ENTITY_SIZES[entity] || 4
    const isHighlighted = highlightNodes.size > 0 && highlightNodes.has(node.id)
    const isDimmed = highlightNodes.size > 0 && !highlightNodes.has(node.id)

    // Draw node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI)
    ctx.fillStyle = isDimmed ? `${color}33` : color
    ctx.fill()

    if (isHighlighted) {
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.beginPath()
      ctx.arc(node.x, node.y, size + 3, 0, 2 * Math.PI)
      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.stroke()
    }

    // Draw label
    if (showLabels && globalScale > 0.7) {
      const label = node.label || node.id
      const fontSize = Math.max(10 / globalScale, 2)
      ctx.font = `${fontSize}px Inter, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillStyle = isDimmed ? '#ccc' : '#444'
      ctx.fillText(label, node.x, node.y + size + 2)
    }
  }, [showLabels, highlightNodes])

  const linkColor = useCallback((link) => {
    if (highlightNodes.size === 0) return 'rgba(180, 200, 220, 0.3)'
    const srcHighlighted = highlightNodes.has(
      typeof link.source === 'object' ? link.source.id : link.source
    )
    const tgtHighlighted = highlightNodes.has(
      typeof link.target === 'object' ? link.target.id : link.target
    )
    if (srcHighlighted && tgtHighlighted) return 'rgba(74, 144, 217, 0.6)'
    return 'rgba(180, 200, 220, 0.08)'
  }, [highlightNodes])

  const handleZoomToFit = () => {
    if (graphRef.current) graphRef.current.zoomToFit(400, 50)
  }

  return (
    <div className="graph-panel" ref={containerRef}>
      {/* Controls */}
      <div className="graph-controls">
        <button onClick={handleZoomToFit}>
          ✦ Fit View
        </button>
        <button
          className={showLabels ? 'active' : ''}
          onClick={() => setShowLabels(!showLabels)}
        >
          {showLabels ? '🏷 Hide Labels' : '🏷 Show Labels'}
        </button>
      </div>

      {/* Graph */}
      {loading ? (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          height: '100%', color: '#888', fontSize: '14px'
        }}>
          Loading graph data...
        </div>
      ) : (
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => 'replace'}
          linkColor={linkColor}
          linkWidth={0.5}
          linkDirectionalParticles={0}
          onNodeClick={handleNodeClick}
          cooldownTime={3000}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          enableNodeDrag={true}
          nodeLabel=""
        />
      )}

      {/* Node Detail Popover */}
      {selectedNode && detailPos && (
        <div className="node-detail-overlay" onClick={onCloseDetail}>
          <div
            className="node-detail"
            style={{ left: detailPos.x, top: detailPos.y }}
            onClick={(e) => e.stopPropagation()}
          >
            <NodeDetail node={selectedNode} onClose={onCloseDetail} />
          </div>
        </div>
      )}

      {/* Stats */}
      {graphStats && (
        <div className="graph-stats">
          <div className="stat-badge">
            <span className="dot" style={{ background: '#4A90D9' }}></span>
            {graphStats.total_nodes} nodes
          </div>
          <div className="stat-badge">
            <span className="dot" style={{ background: '#27AE60' }}></span>
            {graphStats.total_edges} edges
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="graph-legend">
        <div className="legend-title">Entity Types</div>
        {Object.entries(ENTITY_COLORS).map(([entity, color]) => (
          <div className="legend-item" key={entity}>
            <span className="legend-dot" style={{ background: color }}></span>
            {entity.replace(/([A-Z])/g, ' $1').trim()}
          </div>
        ))}
      </div>
    </div>
  )
}

export default GraphView
