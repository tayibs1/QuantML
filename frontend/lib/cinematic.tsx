"use client";

import { createContext, useContext } from "react";

// True when the shell is in cinematic mode. Pages read this to switch to a
// tighter layout instead of leaning on the shell's fit-to-screen scaling.
const CinematicContext = createContext(false);

export function CinematicProvider({ value, children }: { value: boolean; children: React.ReactNode }) {
  return <CinematicContext.Provider value={value}>{children}</CinematicContext.Provider>;
}

export function useCinematic() {
  return useContext(CinematicContext);
}
