import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppShell from "../AppShell";
import App from "../../../App";
import { logout } from "../../../api";
import { clearSession } from "../../../auth";

vi.mock("../../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../api")>();
  return { ...actual, logout: vi.fn().mockResolvedValue(undefined) };
});
vi.mock("../../../auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../auth")>();
  return { ...actual, clearSession: vi.fn() };
});

function renderShell(initialPath = "/batches") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AppShell>
        <div>page body</div>
      </AppShell>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("renders the sidebar with the 3 primary links", () => {
    renderShell();
    expect(screen.getByRole("link", { name: /batches/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /lab/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /registry/i })).toBeInTheDocument();
  });

  function openAccountMenu() {
    const trigger = screen.getByRole("button", { name: "Account menu" });
    fireEvent.pointerDown(trigger, { button: 0, ctrlKey: false, pointerId: 1 });
  }

  it("sign out calls logout and clearSession", async () => {
    renderShell();
    openAccountMenu();
    fireEvent.click(await screen.findByRole("menuitem", { name: "Sign out" }));
    await waitFor(() => {
      expect(logout).toHaveBeenCalledOnce();
      expect(clearSession).toHaveBeenCalledOnce();
    });
  });

  it("collapse toggle flips data-collapsed and persists to localStorage", () => {
    const { container } = renderShell();
    const rail = container.querySelector("aside[data-collapsed]")!;
    expect(rail.getAttribute("data-collapsed")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(rail.getAttribute("data-collapsed")).toBe("true");
    expect(localStorage.getItem("tc_rail_collapsed")).toBe("true");
  });

  it("theme toggle flips data-theme on documentElement and its label reflects the current state", () => {
    renderShell();
    let toggle = screen.getByRole("button", { name: "Switch to dark theme" });
    fireEvent.click(toggle);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    toggle = screen.getByRole("button", { name: "Switch to light theme" });
    fireEvent.click(toggle);
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("breadcrumbs show the short uuid for /batches/:uuid", () => {
    renderShell("/batches/abc-123-def-456");
    expect(screen.getByText("abc-123-")).toBeInTheDocument();
  });

  it("EnvBanner renders only when VITE_ENV is sandbox", () => {
    vi.stubEnv("VITE_ENV", "production");
    const { unmount } = renderShell();
    expect(screen.queryByText("Sandbox environment")).not.toBeInTheDocument();
    unmount();

    vi.stubEnv("VITE_ENV", "sandbox");
    renderShell();
    expect(screen.getByText("Sandbox environment")).toBeInTheDocument();
  });

  it("shell markup snapshot is stable in light and dark themes", () => {
    const { container } = renderShell();
    document.documentElement.setAttribute("data-theme", "light");
    expect({
      theme: document.documentElement.getAttribute("data-theme"),
      html: container.innerHTML,
    }).toMatchSnapshot("appshell-light");
    document.documentElement.setAttribute("data-theme", "dark");
    expect({
      theme: document.documentElement.getAttribute("data-theme"),
      html: container.innerHTML,
    }).toMatchSnapshot("appshell-dark");
  });

  it("account menu closes on Escape without navigating away", async () => {
    renderShell();
    openAccountMenu();
    expect(await screen.findByRole("menuitem", { name: "Sign out" })).toBeInTheDocument();
    fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByRole("menuitem", { name: "Sign out" })).not.toBeInTheDocument();
    });
  });

  it("hamburger opens the mobile drawer, and navigating closes it", () => {
    const { container } = renderShell();
    const rail = container.querySelector("aside[data-collapsed]")!;
    expect(rail.getAttribute("data-drawer-open")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(rail.getAttribute("data-drawer-open")).toBe("true");
    fireEvent.click(screen.getByRole("link", { name: "Registry" }));
    expect(rail.getAttribute("data-drawer-open")).toBe("false");
  });

  it("clicking the scrim closes the drawer", () => {
    const { container } = renderShell();
    const rail = container.querySelector("aside[data-collapsed]")!;
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(rail.getAttribute("data-drawer-open")).toBe("true");
    fireEvent.click(container.querySelector('[aria-hidden="true"]')!);
    expect(rail.getAttribute("data-drawer-open")).toBe("false");
  });

  it("login route renders without the shell", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("link", { name: /batches/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Account menu" })).not.toBeInTheDocument();
  });
});
