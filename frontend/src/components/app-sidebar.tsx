'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  AppWindow,
  Bot,
  ChartLine,
  FileText,
  Home,
  Lightbulb,
  LayoutDashboard,
  Radar,
  Rocket,
  Table2,
} from 'lucide-react'
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

// 메뉴 추가: 해당 그룹의 items 배열에 항목만 추가하면 된다.
const MENU_GROUPS = [
  {
    label: '메뉴',
    items: [
      { title: '홈', href: '/', icon: Home },
      { title: 'AI 에이전트', href: '/agent', icon: Bot },
      { title: 'AI 활용 트렌드', href: '/trends', icon: ChartLine },
      { title: 'Opportunity Radar', href: '/radar', icon: Radar },
      { title: 'Product Generator', href: '/product', icon: Lightbulb },
    ],
  },
  {
    label: '샘플',
    items: [
      { title: '텍스트 에디터', href: '/samples/editor', icon: FileText },
      { title: '테이블', href: '/samples/table', icon: Table2 },
      { title: '복합 화면', href: '/samples/dashboard', icon: LayoutDashboard },
      { title: '모달', href: '/samples/modals', icon: AppWindow },
    ],
  },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-3">
        {/* 상단 배너 */}
        <Link
          href="/"
          className="flex items-center gap-3 rounded-lg bg-primary p-3 text-primary-foreground group-data-[collapsible=icon]:size-8 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0"
        >
          <Rocket className="size-5 shrink-0" />
          <div className="grid leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">KT 해커톤</span>
            <span className="text-xs opacity-80">Team Project</span>
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
