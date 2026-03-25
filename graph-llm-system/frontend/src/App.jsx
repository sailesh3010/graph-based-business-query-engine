import { useState, useEffect, useCallback } from 'react'
import GraphView from './components/GraphView'
import ChatPanel from './components/ChatPanel'

const API_BASE = '/api'

function App() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [selectedNode, setSelectedNode] = useState(null)
  const [graphStats, setGraphStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showLabels, setShowLabels] = useState(true)
  const [highlightNodes, setHighlightNodes] = useState(new Set())

  // Load the full graph on mount
  useEffect(() => {
    loadGraph()
    loadStats()
  }, [])

  const loadGraph = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/graph`)
      const data = await res.json()
      // react-force-graph expects "links" not "edges"
      setGraphData({
        nodes: data.nodes,
        links: data.edges.map(e => ({
          source: e.source,
          target: e.target,
          relation: e.relation,
        })),
      })
    } catch (err) {
      console.error('Failed to load graph:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/graph/stats`)
      const data = await res.json()
      setGraphStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }

  const handleNodeClick = useCallback(async (nodeId) => {
    try {
      const res = await fetch(`${API_BASE}/graph/node/${encodeURIComponent(nodeId)}`)
      const data = await res.json()
      setSelectedNode({ id: nodeId, ...data })
    } catch (err) {
      console.error('Failed to load node:', err)
    }
  }, [])

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null)
  }, [])

  const handleHighlightNodes = useCallback((nodeIds) => {
    setHighlightNodes(new Set(nodeIds))
  }, [])

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="header-icon">D</div>
          <div className="header-breadcrumb">
            <span>Mapping</span>
            <span>/</span>
            <strong>Order to Cash</strong>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="main-content">
        <GraphView
          graphData={graphData}
          loading={loading}
          selectedNode={selectedNode}
          graphStats={graphStats}
          showLabels={showLabels}
          setShowLabels={setShowLabels}
          onNodeClick={handleNodeClick}
          onCloseDetail={handleCloseDetail}
          highlightNodes={highlightNodes}
        />
        <ChatPanel
          onHighlightNodes={handleHighlightNodes}
        />
      </div>
    </div>
  )
}

export default App
