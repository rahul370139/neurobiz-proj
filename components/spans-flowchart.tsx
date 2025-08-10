"use client"
import React, { useMemo, useState } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  NodeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'

interface SpanData {
  span_id: string
  parent_id: string | null
  tool: string
  start_ts: number
  end_ts: number
  args_digest?: string
  result_digest?: string
  attributes?: Record<string, any>
}

interface SpanNodeData {
  span: SpanData
  label: string
  type: string
}

// Custom node component with hover tooltip
function SpanNode({ data, selected }: NodeProps<SpanNodeData>) {
  const [showTooltip, setShowTooltip] = useState(false)
  
  const getNodeColor = (tool: string) => {
    if (tool.includes('retrieval')) return '#3b82f6' // blue
    if (tool.includes('call')) return '#10b981' // green  
    if (tool.includes('llm')) return '#8b5cf6' // purple
    if (tool.includes('policy')) return '#f59e0b' // amber
    return '#6b7280' // gray
  }

  const getBorderColor = (tool: string) => {
    if (tool.includes('retrieval')) return '#1d4ed8'
    if (tool.includes('call')) return '#047857'
    if (tool.includes('llm')) return '#7c3aed'
    if (tool.includes('policy')) return '#d97706'
    return '#374151'
  }

  return (
    <div 
      className="relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Handle type="target" position={Position.Top} />
      
      {/* Hover-triggered overlay positioned above the node */}
      {showTooltip && (
        <div className="absolute z-50 p-2 bg-slate-800 text-white text-xs rounded-lg shadow-xl min-w-[220px] -top-32 left-1/2 transform -translate-x-1/2">
          <div className="font-semibold mb-1 text-center border-b border-slate-600 pb-1">{data.type}</div>
          <div className="space-y-1">
            <div><span className="text-slate-300">ID:</span> {data.span.span_id.slice(0, 12)}...</div>
            <div><span className="text-slate-300">Tool:</span> {data.span.tool}</div>
            <div><span className="text-slate-300">Duration:</span> {data.span.end_ts - data.span.start_ts}ms</div>
            {data.span.parent_id && (
              <div><span className="text-slate-300">Parent:</span> {data.span.parent_id.slice(0, 8)}...</div>
            )}
            {data.span.attributes && Object.keys(data.span.attributes).length > 0 && (
              <div>
                <span className="text-slate-300">Attributes:</span>
                <div className="ml-2 mt-1 max-h-16 overflow-y-auto">
                  {Object.entries(data.span.attributes).slice(0, 3).map(([key, value]) => (
                    <div key={key} className="text-[10px] truncate">
                      {key}: {String(value).slice(0, 20)}...
                    </div>
                  ))}
                  {Object.keys(data.span.attributes).length > 3 && (
                    <div className="text-[10px] text-slate-400">
                      +{Object.keys(data.span.attributes).length - 3} more...
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          {/* Arrow pointing to the node */}
          <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-800"></div>
        </div>
      )}

      <div
        className={`flex items-center justify-center rounded-full border-4 bg-white shadow-lg w-24 h-24 text-center ${
          selected ? 'ring-4 ring-blue-300' : ''
        }`}
        style={{
          backgroundColor: getNodeColor(data.span.tool),
          borderColor: getBorderColor(data.span.tool),
          color: 'white'
        }}
      >
        <div className="flex flex-col items-center">
          <div className="text-xs font-bold leading-tight">{data.type}</div>
          <div className="text-[10px] opacity-80 mt-1 leading-none">{data.span.span_id.slice(0, 8)}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

const nodeTypes = {
  spanNode: SpanNode,
}

interface SpansFlowchartProps {
  spans: SpanData[]
}

export function SpansFlowchart({ spans }: SpansFlowchartProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!spans || spans.length === 0) {
      return { nodes: [], edges: [] }
    }

    // Create a map for parent-child relationships
    const spanMap = new Map(spans.map(span => [span.span_id, span]))
    
    // Sort spans by start_ts to get chronological order
    const sortedSpans = [...spans].sort((a, b) => a.start_ts - b.start_ts)
    
    // Create hierarchical layout: determine levels based on parent-child relationships
    const spanLevels = new Map<string, number>()
    const getSpanLevel = (spanId: string, visited = new Set<string>()): number => {
      if (visited.has(spanId)) return 0 // Prevent infinite recursion
      if (spanLevels.has(spanId)) return spanLevels.get(spanId)!
      
      const span = spanMap.get(spanId)
      if (!span || !span.parent_id || !spanMap.has(span.parent_id)) {
        spanLevels.set(spanId, 0)
        return 0
      }
      
      visited.add(spanId)
      const level = getSpanLevel(span.parent_id, visited) + 1
      spanLevels.set(spanId, level)
      return level
    }
    
    sortedSpans.forEach(span => getSpanLevel(span.span_id))
    
    // Group spans by level
    const levelGroups = new Map<number, SpanData[]>()
    sortedSpans.forEach(span => {
      const level = spanLevels.get(span.span_id) || 0
      if (!levelGroups.has(level)) levelGroups.set(level, [])
      levelGroups.get(level)!.push(span)
    })
    
    // Create nodes with better positioning
    const nodes: Node<SpanNodeData>[] = []
    const nodeWidth = 100  // Account for circular node width + margin
    const nodeHeight = 200 // Increased vertical spacing to accommodate overlay boxes
    
    Array.from(levelGroups.entries()).forEach(([level, levelSpans]) => {
      levelSpans.forEach((span, indexInLevel) => {
        // Extract type from tool name
        let type = span.tool
        if (span.tool.includes('retrieval')) {
          type = span.attributes?.data_type || 'Retrieval'
        } else if (span.tool.includes('call')) {
          type = span.attributes?.operation || 'Process'
        } else if (span.tool.includes('llm')) {
          type = span.attributes?.operation || 'LLM'
        } else if (span.tool.includes('policy')) {
          type = span.attributes?.operation || 'Policy'
        }

        // Calculate position for hierarchical layout
        const totalInLevel = levelSpans.length
        const startX = totalInLevel > 1 ? -(totalInLevel - 1) * nodeWidth / 2 : 0
        
        nodes.push({
          id: span.span_id,
          type: 'spanNode',
          position: { 
            x: startX + indexInLevel * nodeWidth,
            y: level * nodeHeight
          },
          data: {
            span,
            label: span.span_id,
            type: type.charAt(0).toUpperCase() + type.slice(1)
          }
        })
      })
    })

    // Create edges based on parent-child relationships and sequential flow
    const edges: Edge[] = []
    
    // Add parent-child edges (hierarchical connections)
    sortedSpans.forEach(span => {
      if (span.parent_id && spanMap.has(span.parent_id)) {
        edges.push({
          id: `${span.parent_id}-${span.span_id}`,
          source: span.parent_id,
          target: span.span_id,
          type: 'smoothstep',
          style: { 
            stroke: '#1f2937', 
            strokeWidth: 3,
            strokeDasharray: '0'
          },
          markerEnd: {
            type: 'arrowclosed',
            color: '#1f2937',
            width: 20,
            height: 20
          },
          animated: true
        })
      }
    })

    // If no parent-child relationships, create sequential flow based on chronological order
    if (edges.length === 0) {
      sortedSpans.forEach((span, index) => {
        if (index > 0) {
          edges.push({
            id: `${sortedSpans[index-1].span_id}-${span.span_id}`,
            source: sortedSpans[index-1].span_id,
            target: span.span_id,
            type: 'smoothstep',
            style: { 
              stroke: '#1f2937', 
              strokeWidth: 3,
              strokeDasharray: '0'
            },
            markerEnd: {
              type: 'arrowclosed',
              color: '#1f2937',
              width: 20,
              height: 20
            },
            animated: true
          })
        }
      })
    }

    return { nodes, edges }
  }, [spans])

  const [nodes] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  if (!spans || spans.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 border rounded-lg">
        No span data available
      </div>
    )
  }

  return (
    <div className="h-[600px] w-full border rounded-lg bg-slate-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
      >
        <Background />
        <Controls />
        <MiniMap 
          nodeColor={(node) => {
            const tool = (node.data as SpanNodeData).span.tool
            if (tool.includes('retrieval')) return '#3b82f6'
            if (tool.includes('call')) return '#10b981'
            if (tool.includes('llm')) return '#8b5cf6'
            if (tool.includes('policy')) return '#f59e0b'
            return '#6b7280'
          }}
          className="!bg-white !border !border-slate-200"
        />
      </ReactFlow>
    </div>
  )
}
