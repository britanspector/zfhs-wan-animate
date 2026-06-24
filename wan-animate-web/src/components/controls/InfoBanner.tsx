export function InfoBanner() {
  return (
    <div className="rounded-xl bg-morandi-info-bg px-4 py-3 text-sm leading-relaxed text-morandi-text">
      <p>动作视频按 <strong>30fps</strong> 处理；超过 <strong>30 秒</strong> 仅取前 30 秒参与生成。</p>
      <p className="mt-1 text-morandi-muted">
        建议使用默认 <strong>468 x 832</strong>；姿态检测在 GPU 上运行，若 ONNX 报错请重启 ComfyUI 后重试。
      </p>
      <p className="mt-1 text-morandi-muted">输出将保留参考视频音轨。</p>
    </div>
  )
}
