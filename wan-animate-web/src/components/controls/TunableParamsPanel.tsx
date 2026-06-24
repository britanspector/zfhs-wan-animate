import { useState } from 'react'
import type { TunableField } from '../../types/workflow'
import {
  TUNABLE_GROUP_LABELS,
  TUNABLE_GROUP_ORDER,
  coerceTunableValue,
  groupTunableFields,
} from '../../types/workflow'

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

export function TunableParamsPanel({
  schema,
  values,
  variantDefaults,
  disabled,
  onChange,
}: TunableParamsPanelProps) {
  const [open, setOpen] = useState(false)

  if (!schema.length) return null

  const grouped = groupTunableFields(schema)

  return (
    <div className="rounded-2xl bg-morandi-surface p-4 shadow-sm ring-1 ring-morandi-border/60">
      <button
        type="button"
        className="flex w-full items-center justify-between text-sm font-medium text-morandi-text"
        onClick={() => setOpen((o) => !o)}
      >
        <span>高级参数（可选）</span>
        <span className="text-morandi-muted">{open ? '收起' : '展开'}</span>
      </button>
      {open && (
        <div className="mt-4 space-y-6">
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
      )}
    </div>
  )
}
