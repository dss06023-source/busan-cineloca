import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Link, Navigate, RouterProvider, type RouteObject } from "react-router";
import { ApiError } from "./api/client";
import { Layout } from "./components/Layout";
import { NoticeGate } from "./components/NoticeGate";
import { NotFound, RouteError } from "./components/RouteError";
import { Ask } from "./pages/Ask";
import { AdminCourses } from "./pages/admin/AdminCourses";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { AdminLogin } from "./pages/admin/AdminLogin";
import { AdminReviews } from "./pages/admin/AdminReviews";
import { AdminSync } from "./pages/admin/AdminSync";
import { StampBook } from "./pages/StampBook";
import { CourseDetail, SavedCourseDetail } from "./pages/CourseDetail";
import { Courses } from "./pages/Courses";
import { LocationDetail } from "./pages/LocationDetail";
import { Home } from "./pages/Home";
import { Sources } from "./pages/Sources";
import { WorkDetail } from "./pages/WorkDetail";
import { Works } from "./pages/Works";

function MePage() {
  return (
    <section className="page">
      <h1>내 기록</h1>
      <StampBook />
      <Link to="/courses">저장한 코스</Link>
      <br />
      <Link to="/sources">데이터 출처·이용 안내</Link>
    </section>
  );
}

export const routes: RouteObject[] = [
  { path: "/admin/login", element: <AdminLogin /> },
  {
    path: "/admin",
    element: <AdminLayout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <Navigate to="/admin/sync" replace /> },
      { path: "sync", element: <AdminSync /> },
      { path: "reviews", element: <AdminReviews /> },
      { path: "courses", element: <AdminCourses /> },
    ],
  },
  {
    element: <Layout />,
    children: [
      {
        // 하단 탭은 남기고 화면 자리에만 오류 안내를 띄운다
        errorElement: <RouteError />,
        children: [
          { path: "/", element: <Home /> },
          { path: "/locations/:id", element: <LocationDetail /> },
          { path: "/works", element: <Works /> },
          { path: "/works/:id", element: <WorkDetail /> },
          { path: "/ask", element: <Ask /> },
          { path: "/courses", element: <Courses /> },
          { path: "/courses/saved/:key", element: <SavedCourseDetail /> },
          { path: "/courses/:id", element: <CourseDetail /> },
          { path: "/me", element: <MePage /> },
          { path: "/sources", element: <Sources /> },
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
];

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 4xx는 다시 시도해도 같으므로 한 번만
        retry: (n, e) => !(e instanceof ApiError && e.status >= 400 && e.status < 500) && n < 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

const router = createBrowserRouter(routes);
const queryClient = makeQueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NoticeGate>
        <RouterProvider router={router} />
      </NoticeGate>
    </QueryClientProvider>
  );
}
