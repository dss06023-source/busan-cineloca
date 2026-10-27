import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Link, RouterProvider, type RouteObject } from "react-router";
import { ApiError } from "./api/client";
import { Layout } from "./components/Layout";
import { NoticeGate } from "./components/NoticeGate";
import { Ask } from "./pages/Ask";
import { StampBook } from "./pages/StampBook";
import { CourseDetail, SavedCourseDetail } from "./pages/CourseDetail";
import { Courses } from "./pages/Courses";
import { LocationDetail } from "./pages/LocationDetail";
import { MapHome } from "./pages/MapHome";
import { Placeholder } from "./pages/Placeholder";
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
  {
    element: <Layout />,
    children: [
      { path: "/", element: <MapHome /> },
      { path: "/locations/:id", element: <LocationDetail /> },
      { path: "/works", element: <Works /> },
      { path: "/works/:id", element: <WorkDetail /> },
      { path: "/ask", element: <Ask /> },
      { path: "/courses", element: <Courses /> },
      { path: "/courses/saved/:key", element: <SavedCourseDetail /> },
      { path: "/courses/:id", element: <CourseDetail /> },
      { path: "/me", element: <MePage /> },
      { path: "/sources", element: <Sources /> },
      { path: "*", element: <Placeholder title="페이지를 찾을 수 없습니다" wp="404" /> },
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
