// Clerk auth provider (graceful).
//
// When VITE_CLERK_PUBLISHABLE_KEY is set, the app is wrapped in Clerk and gated
// behind sign-in, and the API client is given a token getter. When it is unset
// (e.g. a first deploy before keys are configured), the app renders in demo mode
// with no auth so the deployed link is immediately testable.

import { useEffect } from 'react';
import {
  ClerkProvider,
  SignedIn,
  SignedOut,
  RedirectToSignIn,
  useAuth,
} from '@clerk/clerk-react';
import { setAuthTokenGetter } from './api';

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as
  | string
  | undefined;

export const authEnabled = Boolean(PUBLISHABLE_KEY);

function TokenBridge() {
  const { getToken, isSignedIn } = useAuth();
  useEffect(() => {
    setAuthTokenGetter(async () => (isSignedIn ? await getToken() : null));
    return () => setAuthTokenGetter(null);
  }, [getToken, isSignedIn]);
  return null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  if (!authEnabled) {
    // Demo mode: no Clerk configured.
    return <>{children}</>;
  }
  return (
    <ClerkProvider publishableKey={PUBLISHABLE_KEY!}>
      <TokenBridge />
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </ClerkProvider>
  );
}
