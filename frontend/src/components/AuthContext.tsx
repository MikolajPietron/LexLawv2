'use client';

import React, { createContext, useContext, useState } from 'react';
import AuthModal from './AuthModal';

interface AuthContextType {
  openSignIn: () => void;
  openSignUp: () => void;
}

const AuthContext = createContext<AuthContextType>({
  openSignIn: () => {},
  openSignUp: () => {},
});

export const useAuthModal = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<'sign-in' | 'sign-up'>('sign-in');

  const openSignIn = () => { setView('sign-in'); setOpen(true); };
  const openSignUp = () => { setView('sign-up'); setOpen(true); };

  return (
    <AuthContext.Provider value={{ openSignIn, openSignUp }}>
      {children}
      <AuthModal open={open} onClose={() => setOpen(false)} initialView={view} />
    </AuthContext.Provider>
  );
}