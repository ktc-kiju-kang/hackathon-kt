// 사이드바 메뉴 목록. 기능마다 **import 한 줄 + 항목 한 줄**만 추가한다.
// 이 파일은 .gitattributes에서 merge=union이라, 세 사람이 동시에 줄을 추가해도 git이 양쪽을 모두 살린다.
// 그래서 한 줄에 하나씩, 기존 줄은 고치지 않는다 (같은 줄을 바꾸면 두 버전이 다 남아 lint가 잡는다).
// 순서는 order 숫자 (작을수록 위). 아이콘: https://lucide.dev/icons
import type { LucideIcon } from 'lucide-react'
import { Home } from 'lucide-react'
import { Bot } from 'lucide-react'

export type MenuItem = { title: string; href: string; icon: LucideIcon; order: number }

export const MENU_ITEMS: MenuItem[] = [
  { title: '홈', href: '/', icon: Home, order: 0 },
  { title: 'AI 에이전트', href: '/agent', icon: Bot, order: 90 },
]
