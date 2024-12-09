export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center p-24">
      <h1 className="text-4xl font-bold mb-8">File Converter</h1>
      
      {/* 文件上传组件 */}
      <div className="w-full max-w-2xl">
        <input
          type="file"
          multiple
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100"
        />
      </div>

      {/* 格式选择和转换按钮 */}
      <div className="mt-8 flex gap-4">
        <select className="p-2 border rounded">
          <option value="pdf-to-word">PDF to Word</option>
          <option value="word-to-pdf">Word to PDF</option>
          <option value="jpg-to-png">JPG to PNG</option>
          <option value="png-to-jpg">PNG to JPG</option>
        </select>
        <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Convert
        </button>
      </div>

      {/* 语言切换 */}
      <div className="absolute top-4 right-4">
        <select className="p-2 border rounded">
          <option value="en">English</option>
          <option value="zh">中文</option>
        </select>
      </div>
    </main>
  )
} 