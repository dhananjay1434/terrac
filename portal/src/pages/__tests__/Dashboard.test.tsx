import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../Dashboard";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard page", () => {
  it("renders the Dashboard heading", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });
});
