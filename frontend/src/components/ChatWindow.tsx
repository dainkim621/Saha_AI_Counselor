type Message = {
  id: number;
  text: string;
  sender: "user" | "bot";
};

type ChatWindowProps = {
  messages: Message[];
};

function ChatWindow({ messages }: ChatWindowProps) {
  return (
    <div className="mb-4 h-96 overflow-y-auto rounded-2xl bg-slate-50 p-4">
      <div className="flex flex-col gap-3">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`max-w-xs rounded-2xl p-3 text-sm shadow ${
              message.sender === "user"
                ? "ml-auto rounded-tr-md bg-blue-500 text-white"
                : "rounded-tl-md bg-white text-slate-700"
            }`}
          >
            {message.text}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ChatWindow;