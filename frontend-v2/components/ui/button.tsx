import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
const variants = cva('inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors disabled:opacity-40 disabled:pointer-events-none', {variants:{variant:{default:'bg-blue-600 text-white hover:bg-blue-500',outline:'border border-slate-700 bg-slate-900 hover:bg-slate-800'}},defaultVariants:{variant:'default'}});
export function Button({className,variant,asChild=false,...props}:React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof variants> & {asChild?:boolean}) {const Comp=asChild?Slot:'button';return <Comp className={twMerge(clsx(variants({variant}),className))} {...props}/>}
