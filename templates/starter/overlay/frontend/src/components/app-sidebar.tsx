'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Bot, Home, Sparkles } from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'

// 메뉴 추가: 해당 그룹의 items 배열에 항목만 추가하면 된다 (/add-page).
// 사용자 흐름 순서대로 둔다. UI 샘플(/samples/*)은 주소로만 들어간다.
const MENU_GROUPS = [
  {
    label: '메뉴',
    items: [
      { title: '홈', href: '/', icon: Home },
      { title: 'AI 에이전트', href: '/agent', icon: Bot },
    ],
  },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-3">
        {/* 상단 배너 — KDS: 큰 면을 포인트 색(검정)으로 칠하지 않는다 */}
        <Link
          href="/"
          className="flex items-center gap-3 rounded-lg p-3 text-sidebar-foreground hover:bg-sidebar-accent group-data-[collapsible=icon]:size-8 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0"
        >
          <Sparkles className="size-5 shrink-0" />
          <div className="grid leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">서비스 이름</span>
            <span className="text-xs text-muted-foreground">팀 이름</span>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {MENU_GROUPS.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map(({ title, href, icon: Icon }) => (
                  <SidebarMenuItem key={href}>
                    <SidebarMenuButton asChild tooltip={title} isActive={pathname === href}>
                      <Link href={href}>
                        <Icon />
                        <span>{title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
