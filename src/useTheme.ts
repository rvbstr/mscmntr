import { useEffect, useState } from "react";
export type Theme = "light" | "dark";
const STORAGE_KEY = "art-calendar:theme";
function preferredTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* Storage can be disabled. */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(preferredTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "dark" ? "#111111" : "#ffffff");
  }, [theme]);
  const toggleTheme = () =>
    setTheme((previous) => {
      const next = previous === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* Keep session state. */
      }
      return next;
    });
  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const followSystem = () => {
      try {
        if (localStorage.getItem(STORAGE_KEY)) return;
      } catch {
        return;
      }
      setTheme(query.matches ? "dark" : "light");
    };
    query.addEventListener("change", followSystem);
    return () => query.removeEventListener("change", followSystem);
  }, []);
  return { theme, toggleTheme };
}
