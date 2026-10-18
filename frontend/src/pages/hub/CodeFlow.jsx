import { Background, Controls, Handle, MarkerType, Position, ReactFlow } from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import { Tag, Tooltip } from 'antd'
import '@xyflow/react/dist/style.css'

const NODE_WIDTH = 200
const NODE_HEIGHT = 70

function layout(codeNodes, codeEdges) {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 60 })
  g.setDefaultEdgeLabel(() => ({}))
  codeNodes.forEach((n) => g.setNode(n.key, { width: NODE_WIDTH, height: NODE_HEIGHT }))
  codeEdges.forEach(([src, dst]) => g.setEdge(src, dst))
  dagre.layout(g)

  const positions = {}
  codeNodes.forEach((n) => {
    const { x, y } = g.node(n.key)
    positions[n.key] = { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 }
  })
  return positions
}

function ItemNode({ data, selected }) {
  const isTool = data.type === 'tool'
  return (
    <Tooltip title={data.steps.length ? `업무 단계: ${data.steps.join(', ')}` : '연결된 업무 단계 없음'}>
      <div
        className={`flow-node flow-node-${data.type}${selected ? ' selected' : ''}`}
        style={{ opacity: data.dimmed ? 0.3 : 1 }}
      >
        <Handle type="target" position={Position.Top} />
        <Tag color={isTool ? 'blue' : 'green'}>{(isTool ? data.data_source : data.output_type) || data.type}</Tag>
        {data.deprecated ? <Tag>폐기</Tag> : null}
        <div className="flow-node-name">{data.name}</div>
        <Handle type="source" position={Position.Bottom} />
      </div>
    </Tooltip>
  )
}

const nodeTypes = { toolNode: ItemNode, skillNode: ItemNode }

/** highlighted: 강조할 node key Set (null이면 전체 표시) */
export default function CodeFlow({ codeNodes, codeEdges, steps, highlighted, selectedKey, onNodeClick }) {
  const positions = layout(codeNodes, codeEdges)
  const dimmed = (key) => highlighted != null && !highlighted.has(key)

  const nodes = codeNodes.map((n) => ({
    id: n.key,
    type: `${n.type}Node`,
    position: positions[n.key],
    selected: n.key === selectedKey,
    data: {
      ...n,
      dimmed: dimmed(n.key),
      steps: steps.filter((s) => s.code_nodes?.includes(n.key)).map((s) => s.title),
    },
  }))

  const edges = codeEdges.map(([src, dst]) => ({
    id: `${src}-${dst}`,
    source: src,
    target: dst,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { opacity: dimmed(src) || dimmed(dst) ? 0.3 : 1 },
  }))

  return (
    <div style={{ height: 600 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        fitView
        fitViewOptions={{ maxZoom: 1 }}
        onNodeClick={(_, node) => onNodeClick(node.id)}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
