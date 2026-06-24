import type { WorkflowVariantConfig } from '../../types/workflow'
import { Chip } from '../common/Chip'

interface WorkflowPresetSelectorProps {
  variants: WorkflowVariantConfig[]
  selected: string
  disabled?: boolean
  onChange: (variant: string) => void
}

export function WorkflowPresetSelector({
  variants,
  selected,
  disabled,
  onChange,
}: WorkflowPresetSelectorProps) {
  return (
    <div className="rounded-2xl bg-morandi-surface p-4 shadow-sm ring-1 ring-morandi-border/60">
      <p className="mb-2 text-sm font-medium text-morandi-text">工作流预设</p>
      <div className="flex flex-col gap-3 sm:flex-row">
        {variants.map((v) => (
          <div key={v.variant} className="flex-1">
            <Chip
              label={v.label}
              active={selected === v.variant}
              onClick={() => !disabled && onChange(v.variant)}
            />
            <p className="mt-1 px-1 text-xs text-morandi-muted">{v.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
