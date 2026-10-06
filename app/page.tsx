import { redirect } from "next/navigation"

export default function Page() {
  const username = process.env.MAIN_BOT_USERNAME?.replace(/^@/, "")

  if (username) {
    redirect(`https://t.me/${username}`)
  }

  return null
}
