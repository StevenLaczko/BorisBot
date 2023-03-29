from src.helpers import Message


class Reminder:
    def __init__(self, content, userID, remindType, channelID, serverID, dateTime, isActive=True):
        self.content: Message = content
        self.userID = userID
        self.remindType = remindType
        self.channelID = channelID
        self.serverID = serverID
        self.dateTime = dateTime
        self.isActive = isActive

