import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ParcelMap from "./ParcelMap";

describe("ParcelMap component", () => {
  it("renders map container and GeoJSON textarea", () => {
    render(<ParcelMap />);
    expect(screen.getByTestId("parcel-leaflet-map")).toBeInTheDocument();
    expect(screen.getByLabelText(/Boundary GeoJSON/i)).toBeInTheDocument();
  });

  it("calls onPolygonCreated when valid GeoJSON is typed or pasted into textarea", () => {
    const onCreated = vi.fn();
    render(<ParcelMap onPolygonCreated={onCreated} />);

    const textarea = screen.getByLabelText(/Boundary GeoJSON/i);
    const validPolygon = {
      type: "Polygon",
      coordinates: [
        [
          [77.20, 28.61],
          [77.22, 28.61],
          [77.22, 28.62],
          [77.20, 28.62],
          [77.20, 28.61],
        ],
      ],
    };

    fireEvent.change(textarea, { target: { value: JSON.stringify(validPolygon) } });

    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ type: "Polygon" }));
  });

  it("shows error chip when invalid JSON is entered", () => {
    render(<ParcelMap />);

    const textarea = screen.getByLabelText(/Boundary GeoJSON/i);
    fireEvent.change(textarea, { target: { value: "{ invalid json }" } });

    expect(screen.getByText("JSON syntax error")).toBeInTheDocument();
  });
});
