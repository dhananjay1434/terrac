import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "../Login";
import { login, ApiError } from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, login: vi.fn() };
});

const mockLogin = vi.mocked(login);

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Login />
    </MemoryRouter>,
  );
}

describe("Login page", () => {
  beforeEach(() => vi.clearAllMocks());

  it("show/hide toggle flips the password input type", () => {
    renderPage();
    const pw = screen.getByLabelText("Password") as HTMLInputElement;
    expect(pw.type).toBe("password");
    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(pw.type).toBe("text");
    fireEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(pw.type).toBe("password");
  });

  it("shows the inline error on invalid credentials", async () => {
    mockLogin.mockRejectedValue(new ApiError(401, "unauthorized"));
    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("Invalid email or password."),
    ).toBeInTheDocument();
    expect(mockLogin).toHaveBeenCalledWith("a@b.c", "wrong");
  });
});
