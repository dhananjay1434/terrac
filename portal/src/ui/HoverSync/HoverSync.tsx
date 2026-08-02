import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/** One shared hover time (epoch_ms) for all charts of a single burn, so their
 * crosshairs move together (blueprint audit F2). `null` = not hovering. */
interface HoverSyncValue {
  hoverT: number | null;
  setHoverT: (t: number | null) => void;
}
const HoverSyncContext = createContext<HoverSyncValue>({ hoverT: null, setHoverT: () => {} });

export function HoverSync({ children }: { children: ReactNode }) {
  const [hoverT, setHoverT] = useState<number | null>(null);
  const value = useMemo(() => ({ hoverT, setHoverT }), [hoverT]);
  return <HoverSyncContext.Provider value={value}>{children}</HoverSyncContext.Provider>;
}

export function useHoverSync(): HoverSyncValue {
  return useContext(HoverSyncContext);
}
