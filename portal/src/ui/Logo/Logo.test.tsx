import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Logo from "./Logo";

describe("Logo", () => {
  it("renders an accessible SVG mark with the default TerraCipher label", () => {
    const { getByRole } = render(<Logo />);
    const svg = getByRole("img", { name: "TerraCipher" });
    expect(svg.tagName.toLowerCase()).toBe("svg");
  });

  it("honors an explicit size and custom title", () => {
    const { getByRole } = render(<Logo size={48} title="Home" />);
    const svg = getByRole("img", { name: "Home" });
    expect(svg.getAttribute("width")).toBe("48");
    expect(svg.getAttribute("height")).toBe("48");
  });

  it("forwards svg props (e.g. aria-hidden) through to the element", () => {
    const { container } = render(<Logo aria-hidden />);
    expect(container.querySelector("svg")?.getAttribute("aria-hidden")).toBe(
      "true",
    );
  });
});
