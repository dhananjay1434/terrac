import { describe, it, expect, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "./pages/Login";

/** Smoke test: dark mode mounts without throwing and key text is present.
 * Visual correctness (contrast, no stray light-mode surfaces) is confirmed
 * manually per Part 1.8's gate — this only guards against a future
 * regression that breaks dark-mode rendering outright. */
describe("dark mode smoke test", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-theme");
  });

  it("renders the Login page under data-theme=dark without throwing", () => {
    document.documentElement.dataset.theme = "dark";
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading")).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });
});
