import { createBrowserRouter, Navigate, Outlet } from "react-router";
import { DashboardScreen } from "./Pages/Dashboard";

export const router = createBrowserRouter([
  {path: "/dashboard", Component: DashboardScreen}
])