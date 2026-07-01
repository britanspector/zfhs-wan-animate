import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { TunableField } from '../../types/workflow'
import {
  TUNABLE_GROUP_LABELS,
  TUNABLE_GROUP_ORDER,
  coerceTunableValue,
  groupTunableFields,
} from '../../types/workflow'

const PANEL_WIDTH = 480
const PANEL_GAP = 8
const PANEL_MAX_HEIGHT = 600
const VIEWPORT_MARGIN = 16

type PanelPosition = {
  top: number
  left: number
  maxHeight: number
}

function asBool(value: string | number | boolean, field: TunableField) {
  return coerceTunableValue(field, value) as boolean
}

function loraEnabled(value: string | number | boolean | undefined) {
  return Number(value ?? 0) > 0
}

interface TunableParamsPanelProps {
  schema: TunableField[]
  values: Record<string, string | number | boolean>
  variantDefaults: Record<string, string | number | boolean>
  disabled?: boolean
  onChange: (key: string, value: string | number | boolean) => void
}

function renderField(
  field: TunableField,
  values: Record<string, string | number | boolean>,
  variantDefaults: Record<string, string | number | boolean>,
  disabled: boolean | undefined,
  onChange: (key: string, value: string | number | boolean) => void,
) {
  return (
    <div key={field.key}>
      <label className="block text-sm text-morandi-text">{field.label}</label>
      {field.type === 'float' && (
        <div className="mt-1 flex items-center gap-3">
          <input
            type="range"
            min={field.min ?? 0}
            max={field.max ?? 1}
            step={field.step ?? 0.05}
            value={Number(values[field.key] ?? 0)}
            disabled={disabled}
            onChange={(e) => onChange(field.key, Number(e.target.value))}
            className="flex-1"
          />
          <span className="w-12 text-right text-sm tabular-nums text-morandi-muted">
            {Number(values[field.key] ?? 0).toFixed(2)}
          </span>
        </div>
      )}
      {field.type === 'int' && (
        <input
          type="number"
          min={field.min ?? 1}
          max={field.max ?? 8}
          step={field.step ?? 1}
          value={Number(values[field.key] ?? field.min ?? 1)}
          disabled={disabled}
          onChange={(e) => onChange(field.key, Math.round(Number(e.target.value)))}
          className="mt-1 w-full rounded-lg border border-morandi-border bg-white px-3 py-2 text-sm"
        />
      )}
      {field.type === 'bool' && (
        <label className="mt-2 flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={asBool(values[field.key] ?? false, field)}
            disabled={disabled}
            onChange={(e) => onChange(field.key, e.target.checked)}
          />
          <span>{asBool(values[field.key] ?? false, field) ? '开启' : '关闭'}</span>
        </label>
      )}
      {field.type === 'select' && (
        <select
          className="mt-1 w-full rounded-lg border border-morandi-border bg-white px-3 py-2 text-sm"
          value={String(values[field.key] ?? field.options?.[0] ?? '')}
          disabled={disabled}
          onChange={(e) => onChange(field.key, e.target.value)}
        >
          {(field.options ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      )}
      {field.type === 'text' && (
        <textarea
          rows={field.rows ?? 4}
          value={String(values[field.key] ?? '')}
          disabled={disabled}
          onChange={(e) => onChange(field.key, e.target.value)}
          className="mt-1 w-full rounded-lg border border-morandi-border bg-white px-3 py-2 text-sm leading-relaxed"
        />
      )}
      {field.type === 'lora_switch' && (
        <div className="mt-2 space-y-2">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={loraEnabled(values[field.key])}
              disabled={disabled}
              onChange={(e) => {
                if (e.target.checked) {
                  const fallback = Number(variantDefaults[field.key] ?? 1)
                  onChange(field.key, fallback > 0 ? fallback : 1)
                } else {
                  onChange(field.key, 0)
                }
              }}
            />
            <span>{loraEnabled(values[field.key]) ? '已启用' : '已关闭'}</span>
          </label>
          {loraEnabled(values[field.key]) && (
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={Number(values[field.key] ?? 0)}
                disabled={disabled}
                onChange={(e) => onChange(field.key, Number(e.target.value))}
                className="flex-1"
              />
              <span className="w-12 text-right text-sm tabular-nums text-morandi-muted">
                {Number(values[field.key] ?? 0).toFixed(2)}
              </span>
            </div>
          )}
        </div>
      )}
      {field.hint && <p className="mt-1 text-xs text-morandi-muted">{field.hint}</p>}
    </div>
  )
}

function computePanelPosition(trigger: HTMLElement): PanelPosition {
  const rect = trigger.getBoundingClientRect()
  const viewportW = window.innerWidth
  const viewportH = window.innerHeight
  const panelWidth = Math.min(PANEL_WIDTH, viewportW - VIEWPORT_MARGIN * 2)
  const maxPanelHeight = Math.min(PANEL_MAX_HEIGHT, viewportH * 0.7)

  let left = rect.left
  if (left + panelWidth > viewportW - VIEWPORT_MARGIN) {
    left = viewportW - panelWidth - VIEWPORT_MARGIN
  }
  left = Math.max(VIEWPORT_MARGIN, left)

  const spaceBelow = viewportH - rect.bottom - PANEL_GAP - VIEWPORT_MARGIN
  const spaceAbove = rect.top - PANEL_GAP - VIEWPORT_MARGIN
  const openBelow = spaceBelow >= Math.min(maxPanelHeight, 200) || spaceBelow >= spaceAbove

  if (openBelow) {
    return {
      top: rect.bottom + PANEL_GAP,
      left,
      maxHeight: Math.min(maxPanelHeight, spaceBelow),
    }
  }

  const actualMax = Math.min(maxPanelHeight, spaceAbove)
  return {
    top: Math.max(VIEWPORT_MARGIN, rect.top - PANEL_GAP - actualMax),
    left,
    maxHeight: actualMax,
  }
}

function TunableParamsContent({
  grouped,
  values,
  variantDefaults,
  disabled,
  onChange,
}: {
  grouped: Map<string, TunableField[]>
  values: Record<string, string | number | boolean>
  variantDefaults: Record<string, string | number | boolean>
  disabled?: boolean
  onChange: (key: string, value: string | number | boolean) => void
}) {
  return (
    <div className="space-y-6">
      {TUNABLE_GROUP_ORDER.map((group) => {
        const fields = grouped.get(group)
        if (!fields?.length) return null
        return (
          <div key={group}>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-morandi-muted">
              {TUNABLE_GROUP_LABELS[group]}
            </p>
            <div className="space-y-4">
              {fields.map((field) =>
                renderField(field, values, variantDefaults, disabled, onChange),
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function TunableParamsPanel({
  schema,
  values,
  variantDefaults,
  disabled,
  onChange,
}: TunableParamsPanelProps) {
  const [open, setOpen] = useState(false)
  const [panelPos, setPanelPos] = useState<PanelPosition | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  const close = useCallback(() => setOpen(false), [])

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return
    setPanelPos(computePanelPosition(triggerRef.current))
  }, [])

  useLayoutEffect(() => {
    if (!open) {
      setPanelPos(null)
      return
    }
    updatePosition()
  }, [open, updatePosition])

  useEffect(() => {
    if (!open) return

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    const onResize = () => updatePosition()

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('resize', onResize)
    window.addEventListener('scroll', onResize, true)

    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('resize', onResize)
      window.removeEventListener('scroll', onResize, true)
      document.body.style.overflow = prevOverflow
    }
  }, [open, close, updatePosition])

  if (!schema.length) return null

  const grouped = groupTunableFields(schema)
  const panelWidth = panelPos
    ? Math.min(PANEL_WIDTH, window.innerWidth - VIEWPORT_MARGIN * 2)
    : PANEL_WIDTH

  return (
    <>
      <div className="card">
        <button
          ref={triggerRef}
          type="button"
          disabled={disabled}
          className="flex w-full items-center justify-between text-sm font-medium text-morandi-text disabled:cursor-not-allowed disabled:opacity-50"
          onClick={() => {
            if (disabled) return
            setOpen((o) => !o)
          }}
          aria-expanded={open}
          aria-haspopup="dialog"
        >
          <span>高级参数（可选）</span>
          <span className="text-morandi-muted">{open ? '收起' : '展开'}</span>
        </button>
      </div>

      {open &&
        panelPos &&
        createPortal(
          <>
            <button
              type="button"
              className="fixed inset-0 z-40 bg-black/20"
              aria-label="关闭高级参数"
              onClick={close}
            />
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="tunable-params-title"
              className="fixed z-50 overflow-y-auto rounded-2xl border border-morandi-border bg-white p-4 shadow-lg"
              style={{
                top: panelPos.top,
                left: panelPos.left,
                width: panelWidth,
                maxHeight: panelPos.maxHeight,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 id="tunable-params-title" className="text-sm font-medium text-morandi-text">
                  高级参数（可选）
                </h2>
                <button
                  type="button"
                  className="text-sm text-morandi-muted hover:text-morandi-primary"
                  onClick={close}
                >
                  收起
                </button>
              </div>
              <TunableParamsContent
                grouped={grouped}
                values={values}
                variantDefaults={variantDefaults}
                disabled={disabled}
                onChange={onChange}
              />
            </div>
          </>,
          document.body,
        )}
    </>
  )
}
