'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { EMPLOYEES } from './data'

function Demo({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function FormDialog() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)

  // 닫을 때 입력값·오류 초기화. 제어형 Dialog는 setOpen(false)로는 onOpenChange가 불리지 않으므로 직접 호출한다.
  const onOpenChange = (next: boolean) => {
    setOpen(next)
    if (!next) {
      setName('')
      setEmail('')
      setError(null)
    }
  }

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return setError('이름을 입력하세요.')
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError('이메일 형식이 올바르지 않습니다.')
    toast.success(`${name} 님을 초대했습니다`)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button>멤버 초대</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={submit} noValidate className="space-y-4">
          <DialogHeader>
            <DialogTitle>멤버 초대</DialogTitle>
            <DialogDescription>이름과 이메일을 입력하면 초대 메일이 발송됩니다. (샘플: 실제 발송 없음)</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="invite-name">이름</Label>
            <Input id="invite-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="invite-email">이메일</Label>
            <Input id="invite-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                취소
              </Button>
            </DialogClose>
            <Button type="submit">초대하기</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function NestedDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">중첩 모달 열기</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>첫 번째 모달</DialogTitle>
          <DialogDescription>이 안에서 다시 모달을 열 수 있습니다. ESC를 누르면 가장 위의 모달부터 닫힙니다.</DialogDescription>
        </DialogHeader>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="secondary">두 번째 모달 열기</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>두 번째 모달</DialogTitle>
              <DialogDescription>중첩된 모달입니다.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button>닫기</Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </DialogContent>
    </Dialog>
  )
}

export function ModalsSample() {
  const employee = EMPLOYEES[0]

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Demo title="폼 모달" description="입력 검증, 오류 표시, 닫을 때 초기화, 성공 시 토스트">
        <FormDialog />
      </Demo>

      <Demo title="확인 다이얼로그" description="되돌릴 수 없는 작업 전 확인 (AlertDialog)">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive">계정 삭제</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>정말 삭제하시겠습니까?</AlertDialogTitle>
              <AlertDialogDescription>이 작업은 되돌릴 수 없습니다. (샘플: 실제로 삭제되지 않습니다)</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>취소</AlertDialogCancel>
              <AlertDialogAction onClick={() => toast.error('삭제했습니다')}>삭제</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Demo>

      <Demo title="상세 시트" description="화면 옆에서 열리는 상세 보기 패널">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline">직원 상세 보기</Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>{employee.name}</SheetTitle>
              <SheetDescription>{employee.email}</SheetDescription>
            </SheetHeader>
            <dl className="grid grid-cols-[5rem_1fr] gap-y-3 px-4 text-sm">
              <dt className="text-muted-foreground">부서</dt>
              <dd>{employee.department}</dd>
              <dt className="text-muted-foreground">직급</dt>
              <dd>{employee.role}</dd>
              <dt className="text-muted-foreground">상태</dt>
              <dd>
                <Badge variant="secondary">{employee.status}</Badge>
              </dd>
              <dt className="text-muted-foreground">입사일</dt>
              <dd>{employee.joinedAt}</dd>
            </dl>
            <SheetFooter>
              <Button onClick={() => toast.info('메시지를 보냈습니다')}>메시지 보내기</Button>
            </SheetFooter>
          </SheetContent>
        </Sheet>
      </Demo>

      <Demo title="중첩 모달" description="모달 안에서 모달 열기">
        <NestedDialog />
      </Demo>

      <Demo title="토스트" description="비차단 알림 (sonner)">
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => toast.success('저장했습니다')}>
            성공
          </Button>
          <Button variant="outline" onClick={() => toast.error('오류가 발생했습니다')}>
            오류
          </Button>
          <Button variant="outline" onClick={() => toast.info('새 알림이 있습니다')}>
            정보
          </Button>
          <Button
            variant="outline"
            onClick={() => toast.promise(new Promise((r) => setTimeout(r, 1500)), { loading: '처리 중...', success: '완료했습니다', error: '실패했습니다' })}
          >
            진행 상태
          </Button>
        </div>
      </Demo>
    </div>
  )
}
