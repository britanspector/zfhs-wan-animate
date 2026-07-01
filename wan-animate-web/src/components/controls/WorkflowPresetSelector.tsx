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
    <div className="card">
      <p className="mb-2 text-sm font-medium text-morandi-text">中升智学动作迁移实验项目工作流</p>
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
