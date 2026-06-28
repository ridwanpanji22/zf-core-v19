import { redirect } from "next/navigation";

export default function RootPage() {
  // Redirect standard base route dynamically to protected dashboard
  redirect("/dashboard");
}
