import { QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'

import { queryClient } from '@/app/query-client'
import { AuthProvider } from '@/features/auth'


type AppProvidersProps = PropsWithChildren

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
}