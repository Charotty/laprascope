type Props = {
  value: number;
};

export default function ProgressBar({ value }: Props) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div
      style={{
        width: '100%',
        height: 10,
        borderRadius: 999,
        overflow: 'hidden',
        border: '1px solid rgba(255, 255, 255, 0.14)',
        background: 'rgba(255, 255, 255, 0.06)'
      }}
      aria-label={`progress ${clamped}%`}
    >
      <div
        style={{
          width: `${clamped}%`,
          height: '100%',
          background: '#5b7cff'
        }}
      />
    </div>
  );
}
