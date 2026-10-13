import { useNavigate } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SharedPostCard = ({ shared }) => {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      data-testid={`shared-post-card-${shared.post_id}`}
      onClick={() => navigate(`/post/${shared.post_id}`)}
      className="block w-56 max-w-full text-left rounded-xl overflow-hidden bg-white text-gray-900 border border-gray-200 transition-transform duration-200 hover:-translate-y-0.5"
    >
      <div className="px-3 py-2 font-manrope text-xs font-semibold truncate">{shared.author_name || "Looksy creator"}</div>
      <img src={`${BACKEND_URL}/api/images/${shared.image_id}`} alt="Shared post" className="w-full aspect-square object-cover" />
      {shared.caption && <p className="px-3 py-2 font-manrope text-xs text-gray-600 line-clamp-2">{shared.caption}</p>}
    </button>
  );
};

export const MessageContent = ({ message }) => {
  const shared = message.shared_post;
  if (!shared) return <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>;
  return (
    <div className="space-y-2">
      <SharedPostCard shared={shared} />
      {shared.has_note && <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>}
    </div>
  );
};
