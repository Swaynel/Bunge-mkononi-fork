import BillPdfViewer from '@/components/BillPdfViewer';
import { getBillPdfSourceUrl } from '@/lib/pdf';
import { BillDetail } from '@/types';

interface BillDocumentReaderProps {
  bill: BillDetail;
}

export default function BillDocumentReader({ bill }: BillDocumentReaderProps) {
  const pdfSourceUrl = getBillPdfSourceUrl(bill);

  return (
    <BillPdfViewer
      billTitle={bill.title}
      pdfUrl={pdfSourceUrl}
      officialUrl={bill.parliamentUrl || bill.fullTextUrl}
    />
  );
}
