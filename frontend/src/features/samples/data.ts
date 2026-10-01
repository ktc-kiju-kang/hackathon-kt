// 샘플 화면 전용 mock 데이터 (백엔드 없음). 결정적으로 생성해 새로고침해도 같다.

export const DEPARTMENTS = ['개발', '디자인', '기획', '마케팅', '영업', '인사'] as const
export const STATUSES = ['재직', '휴직', '출장', '퇴사'] as const
export const ROLES = ['사원', '대리', '과장', '차장', '부장'] as const

export type Department = (typeof DEPARTMENTS)[number]
export type Status = (typeof STATUSES)[number]

export type Employee = {
  id: number
  name: string
  email: string
  department: Department
  role: (typeof ROLES)[number]
  status: Status
  salary: number // 만원
  joinedAt: string // YYYY-MM-DD
}

const SURNAMES = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임']
const GIVEN = ['민준', '서연', '지호', '하은', '도윤', '수아', '예준', '지우', '시우', '채원', '건우', '다은']

export const EMPLOYEES: Employee[] = Array.from({ length: 50 }, (_, i) => {
  const id = i + 1
  const name = `${SURNAMES[(i * 3) % SURNAMES.length]}${GIVEN[(i * 7) % GIVEN.length]}`
  const month = String((i * 5) % 12 + 1).padStart(2, '0')
  const day = String((i * 11) % 28 + 1).padStart(2, '0')
  return {
    id,
    name,
    email: `user${String(id).padStart(2, '0')}@example.com`,
    department: DEPARTMENTS[(i * 5) % DEPARTMENTS.length],
    // 성씨(i % 10 에 의존)와 겹치지 않도록 i / 3, i / 4 항을 섞는다
    role: ROLES[(i * 2 + Math.floor(i / 4)) % ROLES.length],
    status: STATUSES[[0, 0, 0, 1, 0, 2, 0, 0, 3, 0, 1, 0, 0, 2, 0][(i + Math.floor(i / 3)) % 15]],
    salary: 3200 + ((i * 370) % 4800),
    joinedAt: `${2018 + (i % 8)}-${month}-${day}`,
  }
})

export type Activity = { id: number; who: string; action: string; target: string; time: string; team: Department }

export const ACTIVITIES: Activity[] = [
  { id: 1, who: '김민준', action: '배포했습니다', target: 'v1.4.2', time: '방금 전', team: '개발' },
  { id: 2, who: '이서연', action: '시안을 올렸습니다', target: '메인 배너 B안', time: '12분 전', team: '디자인' },
  { id: 3, who: '박지호', action: '문서를 수정했습니다', target: '요구사항 정의서', time: '35분 전', team: '기획' },
  { id: 4, who: '최하은', action: '캠페인을 시작했습니다', target: '가을 프로모션', time: '1시간 전', team: '마케팅' },
  { id: 5, who: '정도윤', action: '계약을 체결했습니다', target: 'A사 연간 계약', time: '2시간 전', team: '영업' },
  { id: 6, who: '강수아', action: '채용 공고를 등록했습니다', target: '백엔드 개발자', time: '3시간 전', team: '인사' },
  { id: 7, who: '조예준', action: '이슈를 닫았습니다', target: '#128 로그인 오류', time: '5시간 전', team: '개발' },
  { id: 8, who: '윤지우', action: '디자인 시스템을 갱신했습니다', target: '버튼 컴포넌트', time: '어제', team: '디자인' },
]

export type Period = 'week' | 'month' | 'year'

export const STATS: Record<Period, { label: string; value: number }[]> = {
  week: [
    { label: '월', value: 42 },
    { label: '화', value: 58 },
    { label: '수', value: 35 },
    { label: '목', value: 71 },
    { label: '금', value: 64 },
    { label: '토', value: 22 },
    { label: '일', value: 18 },
  ],
  month: Array.from({ length: 10 }, (_, i) => ({ label: `${i * 3 + 1}일`, value: 30 + ((i * 37) % 60) })),
  year: ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'].map((label, i) => ({
    label,
    value: 120 + ((i * 53) % 180),
  })),
}
