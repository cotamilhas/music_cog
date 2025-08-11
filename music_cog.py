import discord
from discord.ext import commands
from yt_dlp import YoutubeDL


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        self.vc = None

        self.YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'extractaudio': True,
            'quiet': True,
        }
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    def search_yt(self, query: str):
        try:
            with YoutubeDL(self.YDL_OPTIONS) as ydl:
                results = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not results or "entries" not in results or len(results["entries"]) == 0:
                return None
            info = results["entries"][0]
            return {
                'source': info['url'],
                'title': info['title']
            }
        except Exception as e:
            print(f"[YT SEARCH ERROR] {e}")
            return None

    async def play_next(self, ctx):
        if self.music_queue:
            self.is_playing = True
            song = self.music_queue.pop(0)
            m_url = song[0]['source']

            self.vc.play(
                discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),
                after=lambda e: self.bot.loop.create_task(self.play_next(ctx)) if not e else print(f"[PLAYER ERROR] {e}")
            )
            await ctx.send(f"Now playing: **{song[0]['title']}**")
        else:
            self.is_playing = False
            await ctx.send("Queue is empty, nothing to play.")

    async def play_music(self, ctx):
        if self.music_queue:
            self.is_playing = True
            song = self.music_queue.pop(0)
            m_url = song[0]['source']
            voice_channel = song[1]

            if self.vc is None or not self.vc.is_connected():
                self.vc = await voice_channel.connect()
                if self.vc is None:
                    await ctx.send("Could not connect to the voice channel.")
                    return
            else:
                await self.vc.move_to(voice_channel)

            self.vc.play(
                discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),
                after=lambda e: self.bot.loop.create_task(self.play_next(ctx)) if not e else print(f"[PLAYER ERROR] {e}")
            )
            await ctx.send(f"Now playing: **{song[0]['title']}**")
        else:
            self.is_playing = False

    @commands.command(name='play', aliases=["p"], help='Plays a song from YouTube')
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You must be in a voice channel to play music.")
            return

        if self.is_paused:
            self.vc.resume()
            self.is_paused = False
            await ctx.send("Music resumed.")
            return

        song = self.search_yt(query)
        if song is None:
            await ctx.send("No results found for that search.")
            return

        await ctx.send(f"Added to queue: **{song['title']}**")
        self.music_queue.append((song, ctx.author.voice.channel))

        if not self.is_playing:
            await self.play_music(ctx)

    @commands.command(name='pause', help='Pauses the current song')
    async def pause(self, ctx):
        if self.vc and self.vc.is_playing():
            self.vc.pause()
            self.is_paused = True
            await ctx.send("Music paused.")
        else:
            await ctx.send("Nothing is playing at the moment.")

    @commands.command(name='resume', help='Resumes the paused song')
    async def resume(self, ctx):
        if self.vc and self.is_paused:
            self.vc.resume()
            self.is_paused = False
            await ctx.send("Music resumed.")
        else:
            await ctx.send("There is no paused music to resume.")

    @commands.command(name='skip', help='Skips to the next song')
    async def skip(self, ctx):
        if self.vc and (self.vc.is_playing() or self.is_paused):
            self.vc.stop()
            await ctx.send("Song skipped.")
        else:
            await ctx.send("There is no song to skip.")

    @commands.command(name='queue', help='Shows the music queue')
    async def queue(self, ctx):
        if not self.music_queue:
            await ctx.send("The queue is empty.")
            return

        queue_list = "\n".join([f"{i+1}. {song[0]['title']}" for i, song in enumerate(self.music_queue[:5])])
        await ctx.send(f"Current queue:\n{queue_list}")

    @commands.command(name='clear', help='Clears the music queue')
    async def clear(self, ctx):
        self.music_queue.clear()
        await ctx.send("Music queue cleared.")

    @commands.command(name='leave', help='Leaves the voice channel')
    async def leave(self, ctx):
        self.is_playing = False
        self.is_paused = False
        if self.vc:
            await self.vc.disconnect()
            self.vc = None
            await ctx.send("Left the voice channel.")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
    print("MusicCog loaded successfully.")
