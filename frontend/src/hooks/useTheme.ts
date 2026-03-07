import { useCallback, useEffect, useMemo, useState } from "react";

type ThemeMode = "dark" | "light";

export function useTheme() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = window.localStorage.getItem("rataz-theme") as ThemeMode | null;
    return saved ?? "dark";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    window.localStorage.setItem("rataz-theme", theme);
  }, [theme]);

  const isDark = useMemo(() => theme === "dark", [theme]);
  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return { theme, isDark, toggleTheme };
}
