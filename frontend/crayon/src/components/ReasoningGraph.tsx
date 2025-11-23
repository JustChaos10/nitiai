import { useCallback, useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";

interface CausalEdge {
  from: string;
  to: string;
  strength: number;
  type: "direct" | "indirect" | "confounder";
}

interface CausalGraph {
  nodes: string[];
  edges: CausalEdge[];
}

interface ReasoningGraphProps {
  graph: CausalGraph;
  highlightedNodes?: string[];
  onNodeClick?: (nodeId: string) => void;
}

const NODE_COLORS = {
  default: "#94a3b8",
  highlighted: "#3b82f6",
  cause: "#10b981",
  effect: "#ef4444",
  confounder: "#f59e0b",
};

const EDGE_COLORS = {
  direct: "#3b82f6",
  indirect: "#94a3b8",
  confounder: "#f59e0b",
};

export function ReasoningGraph({ graph, highlightedNodes = [], onNodeClick }: ReasoningGraphProps) {
  // Convert causal graph to React Flow format
  const initialNodes: Node[] = useMemo(() => {
    return graph.nodes.map((nodeId, index) => {
      const isHighlighted = highlightedNodes.includes(nodeId);

      return {
        id: nodeId,
        type: "default",
        position: {
          x: (index % 3) * 250,
          y: Math.floor(index / 3) * 150,
        },
        data: {
          label: nodeId.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
        },
        style: {
          background: isHighlighted ? NODE_COLORS.highlighted : NODE_COLORS.default,
          color: "white",
          border: isHighlighted ? "2px solid #1e40af" : "1px solid #64748b",
          borderRadius: "8px",
          padding: "12px",
          fontSize: "12px",
          fontWeight: isHighlighted ? 600 : 400,
        },
      };
    });
  }, [graph.nodes, highlightedNodes]);

  const initialEdges: Edge[] = useMemo(() => {
    return graph.edges.map((edge, index) => ({
      id: `edge-${index}`,
      source: edge.from,
      target: edge.to,
      type: "smoothstep",
      animated: edge.type === "direct",
      style: {
        stroke: EDGE_COLORS[edge.type] || EDGE_COLORS.direct,
        strokeWidth: Math.max(1, edge.strength * 3),
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: EDGE_COLORS[edge.type] || EDGE_COLORS.direct,
      },
      label: edge.strength.toFixed(2),
      labelStyle: {
        fontSize: 10,
        fill: "#64748b",
      },
    }));
  }, [graph.edges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClickHandler = useCallback(
    (_event: any, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [onNodeClick]
  );

  return (
    <div style={{ width: "100%", height: "500px", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClickHandler}
        fitView
      >
        <Controls />
        <Background color="#94a3b8" gap={16} />
      </ReactFlow>
      <div style={{ padding: "12px", borderTop: "1px solid #e2e8f0", fontSize: "12px", color: "#64748b" }}>
        <strong>Legend:</strong>
        <span style={{ marginLeft: "12px" }}>
          <span style={{ color: EDGE_COLORS.direct }}>● Direct</span>
          <span style={{ marginLeft: "12px", color: EDGE_COLORS.indirect }}>● Indirect</span>
          <span style={{ marginLeft: "12px", color: EDGE_COLORS.confounder }}>● Confounder</span>
        </span>
      </div>
    </div>
  );
}
