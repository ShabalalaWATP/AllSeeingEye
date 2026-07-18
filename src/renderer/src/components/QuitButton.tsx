interface QuitButtonProps {
  className?: string
}

export default function QuitButton({ className = '' }: QuitButtonProps): React.JSX.Element {
  return (
    <button
      type="button"
      className={`icon-btn app-quit no-drag ${className}`.trim()}
      onClick={() => void window.criticalEye.quit()}
      aria-label="Quit AllSeeingEye"
      title="Quit AllSeeingEye"
    >
      ×
    </button>
  )
}
