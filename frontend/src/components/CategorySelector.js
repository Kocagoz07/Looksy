import { useState } from "react";
import { Spade, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function CategorySelector({ currentUser, onCategorySet }) {
  const [loading, setLoading] = useState(false);

  const selectCategory = async (category) => {
    setLoading(true);
    try {
      await axios.patch(
        `${BACKEND_URL}/api/users/me?category=${category}`,
        {},
        { withCredentials: true }
      );
      toast.success(`Welcome to ${category === 'men' ? 'Men' : 'Women'}'s section!`);
      onCategorySet();
    } catch (err) {
      console.error("Error setting category:", err);
      toast.error("Failed to set category");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <h2 className="font-playfair text-3xl sm:text-4xl font-bold mb-4">
        Choose Your Category
      </h2>
      <p className="font-manrope text-lg opacity-70 mb-8">
        Select whether you want to be part of the Men's or Women's fashion community
      </p>
      
      <div className="flex items-center justify-center gap-6">
        <button
          data-testid="category-men-btn"
          onClick={() => selectCategory("men")}
          disabled={loading}
          className="flex flex-col items-center gap-3 p-8 rounded-2xl border-2 border-current hover:bg-current hover:bg-opacity-10 transition-all disabled:opacity-50"
        >
          <div className="w-24 h-24 flex items-center justify-center bg-black text-white rounded-full">
            <Spade className="w-12 h-12" />
          </div>
          <span className="font-playfair text-xl font-semibold">Men</span>
        </button>
        
        <button
          data-testid="category-women-btn"
          onClick={() => selectCategory("women")}
          disabled={loading}
          className="flex flex-col items-center gap-3 p-8 rounded-2xl border-2 border-current hover:bg-current hover:bg-opacity-10 transition-all disabled:opacity-50"
        >
          <div className="w-24 h-24 flex items-center justify-center bg-[#4A0404] text-[#FF0000] rounded-full">
            <Heart className="w-12 h-12 fill-current" />
          </div>
          <span className="font-playfair text-xl font-semibold">Women</span>
        </button>
      </div>
    </div>
  );
}