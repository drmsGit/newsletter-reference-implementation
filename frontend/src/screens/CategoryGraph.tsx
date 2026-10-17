import { useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router'

import { useCategoryDetail, useCategoryGraph, type CategoryGraph as Graph } from '../api/resources'
import { figureColumns } from '../components/ContentFigures'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { CATEGORIES } from './Categories'

type Node = Graph['nodes'][number]
type Edge = Graph['edges'][number]

const WIDTH = 1200
const HEIGHT = 600
const CENTRE = { x: WIDTH / 2, y: HEIGHT / 2 }
/** Dots stay small (2026-10-17, as Obsidian draws them): 4 to 10 px. */
const R_MIN = 4
const R_MAX = 10

/**
 * Where each category sits on the drawing (task-359): main categories on an
 * inner circle, the rest on a wide outer ellipse, so the drawing fills the
 * width; each ring in name order. A dot grows with how often its records were
 * picked, relative to the most picked category, by square root and capped.
 */
export function layout(nodes: Node[]): Map<number, { x: number; y: number; r: number }> {
  const place = new Map<number, { x: number; y: number; r: number }>()
  const most = Math.max(1, ...nodes.map((n) => n.selected_count))
  const ring = (group: Node[], rx: number, ry: number, offset: number) =>
    [...group]
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((node, index) => {
        const angle = offset + (2 * Math.PI * index) / Math.max(group.length, 1)
        place.set(node.id, {
          x: Math.round(CENTRE.x + rx * Math.cos(angle)),
          y: Math.round(CENTRE.y + ry * Math.sin(angle)),
          r: Math.round((R_MIN + (R_MAX - R_MIN) * Math.sqrt(node.selected_count / most)) * 10) / 10,
        })
      })
  ring(nodes.filter((n) => n.type === 'main'), 160, 160, -Math.PI / 2)
  ring(nodes.filter((n) => n.type !== 'main'), 480, 250, -Math.PI / 2 + 0.3)
  return place
}

/** Rising, falling or none: said in words, never drawn. */
function trend(node: { avg_delta: number }): string {
  return node.avg_delta > 0 ? 'rising' : node.avg_delta < 0 ? 'falling' : 'none'
}

function described(node: Node): string {
  return `${node.name}: ${node.content_count} records, picked ${node.selected_count} times, ` +
    `signal ${node.total_delta} (${trend(node)})`
}

/**
 * The category graph (task-359): categories and how they connect, by a
 * parent–child link or by records they share, for this brand's records and
 * audience. Drawn as Obsidian draws a graph (2026-10-17): small dots across
 * the full width, a name only on hover or focus, the dot's links and
 * neighbours lit and the rest faded; a chosen category's details below it, in
 * tables. A redesign of its own is TASK-394.
 */
export default function CategoryGraph() {
  const graph = useCategoryGraph()
  const [selected, setSelected] = useState<number | null>(null)
  const node = graph.data?.nodes.find((n) => n.id === selected)
  return (
    <>
      <h1>Category graph</h1>
      <p className="muted">
        Each dot is a category, bigger when its records were picked more often. Lines link a parent to its
        subcategories and two categories that share records. Point at a dot to see its name and links; choose it to see
        its figures below.
      </p>
      <ScreenState query={graph}>
        {graph.data && (
          <>
            <Drawing graph={graph.data} selected={selected} onSelect={setSelected} />
            {node && <Details key={node.id} node={node} />}
          </>
        )}
      </ScreenState>
    </>
  )
}

function Drawing({ graph, selected, onSelect }: { graph: Graph; selected: number | null; onSelect: (id: number) => void }) {
  const place = layout(graph.nodes)
  const [pointed, setPointed] = useState<number | null>(null)
  // What is lit: the dot pointed at, else the chosen one.
  const active = pointed ?? selected
  const near = new Set<number>()
  if (active != null) {
    near.add(active)
    for (const edge of graph.edges) {
      if (edge.source === active) near.add(edge.target)
      if (edge.target === active) near.add(edge.source)
    }
  }
  const touches = (edge: Edge) => active != null && (edge.source === active || edge.target === active)
  const press = (id: number) => (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect(id)
    }
  }
  return (
    <svg className="graph-drawing" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="group" aria-label="Category graph">
      {graph.edges.map((edge) => {
        const a = place.get(edge.source)
        const b = place.get(edge.target)
        if (!a || !b) return null
        const state = active == null ? '' : touches(edge) ? ' graph-edge--lit' : ' graph-edge--faded'
        return (
          <line
            key={`${edge.source}-${edge.target}`}
            x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            className={`graph-edge graph-edge--${edge.type}${state}`}
          />
        )
      })}
      {graph.nodes.map((n) => {
        const at = place.get(n.id)!
        const state = (selected === n.id ? ' graph-node--selected' : '') +
          (active != null && !near.has(n.id) ? ' graph-node--faded' : '')
        return (
          <g
            key={n.id}
            role="button"
            tabIndex={0}
            aria-label={described(n)}
            aria-pressed={selected === n.id}
            className={`graph-node${state}`}
            onClick={() => onSelect(n.id)}
            onKeyDown={press(n.id)}
            onMouseEnter={() => setPointed(n.id)}
            onMouseLeave={() => setPointed(null)}
            onFocus={() => setPointed(n.id)}
            onBlur={() => setPointed(null)}
          >
            <circle cx={at.x} cy={at.y} r={at.r} />
            {active === n.id && (
              <text x={at.x} y={at.y + at.r + 16} textAnchor="middle" aria-hidden="true">
                {n.name}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

/** A chosen category, below the drawing: every figure in a table. */
function Details({ node }: { node: Node }) {
  const detail = useCategoryDetail(node.id)
  const data = detail.data
  const heading = `graph-details-${node.id}`
  const records = (data?.assigned_content ?? []).map((r) => ({ ...r, id: r.content_id }))
  type RecordRow = (typeof records)[number]
  const recordColumns: DataColumn<RecordRow>[] = [
    { key: 'title', header: 'Record', isRowHeader: true, render: (r) => <Link to={`/content/${r.content_id}`}>{r.title}</Link> },
    ...figureColumns<RecordRow>((r) => r.figures),
  ]
  const relations = [
    ...(data?.parents ?? []).map((c) => ({ id: c.id, relation: 'Under', name: c.name })),
    ...(data?.children ?? []).map((c) => ({ id: c.id, relation: 'Subcategory', name: c.name })),
  ]
  type Figures = { id: number; records: number; picked: number; updates: number; signal: number; average: number }
  const figures: Figures[] = data
    ? [{ id: node.id, records: node.content_count, picked: node.selected_count, updates: data.impact.update_count,
        signal: data.impact.total_delta, average: data.impact.avg_delta }]
    : []
  const round = (value: number) => String(Math.round(value * 10) / 10)
  return (
    <section className="graph-details" aria-labelledby={heading}>
      <h2 id={heading}>{node.name}</h2>
      <ScreenState query={detail}>
        {data && (
          <>
            <p>
              <Link to={`${CATEGORIES}/${node.id}`}>The category's page</Link>
            </p>
            <DataTable
              label={`Figures of ${node.name}`}
              columns={[
                { key: 'records', header: 'Records', numeric: true, render: (f) => String(f.records) },
                { key: 'picked', header: 'Picked', numeric: true, render: (f) => String(f.picked) },
                { key: 'updates', header: 'Signal updates', numeric: true, render: (f) => String(f.updates) },
                { key: 'signal', header: 'Signal', numeric: true, render: (f) => round(f.signal) },
                { key: 'average', header: 'Average per update', numeric: true, render: (f) => round(f.average) },
                { key: 'trend', header: 'Trend', render: (f) => trend({ avg_delta: f.average }) },
              ]}
              items={figures}
              emptyMessage="No figures yet."
            />
            <DataTable
              label={`Relations of ${node.name}`}
              columns={[
                { key: 'relation', header: 'Relation', render: (r) => r.relation },
                { key: 'name', header: 'Category', isRowHeader: true, render: (r) => r.name },
              ]}
              items={relations}
              emptyMessage="No parent and no subcategory."
            />
            <DataTable label={`Records in ${node.name}`} columns={recordColumns} items={records}
              emptyMessage="No record of this brand is in this category." />
          </>
        )}
      </ScreenState>
    </section>
  )
}
