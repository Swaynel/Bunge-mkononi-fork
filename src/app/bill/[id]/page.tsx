import { redirect } from 'next/navigation';

export default async function LegacyBillPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/bills/${id}`);
}
