import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost'

const VARIANT: Record<Variant, string> = {
  primary: 'bg-mill text-white hover:brightness-125',
  secondary: 'border border-line bg-surface text-ink hover:bg-plane',
  ghost: 'text-ink-soft hover:bg-plane hover:text-ink',
}

export function Button({
  variant = 'secondary',
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        'inline-flex min-h-[40px] items-center justify-center gap-2 rounded-lg px-4',
        'text-[14px] font-medium transition',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mill',
        'disabled:pointer-events-none disabled:opacity-50',
        VARIANT[variant],
        className,
      )}
      {...props}
    />
  )
}
