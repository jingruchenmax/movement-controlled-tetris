using UnityEngine;
using System.Net.Sockets;
using System.IO;
using System.Threading;
public class Piece : MonoBehaviour
{
    public Board board { get; private set; }
    public TetrominoData data { get; private set; }
    public Vector3Int[] cells { get; private set; }
    public Vector3Int position { get; private set; }
    public int rotationIndex { get; private set; }

    public float stepDelay = 1f;
    public float moveDelay = 0.1f;
    public float lockDelay = 0.5f;

    private float stepTime;
    private float moveTime;
    private float lockTime;

    private TcpClient tcpClient;
    private StreamReader reader;
    private Thread tcpThread;
    private string lastMessage;
    private string currentInputState = "Neutral";

    public GameObject burst;
    [SerializeField] private CameraEffect cameraEffect;
    public void Initialize(Board board, Vector3Int position, TetrominoData data)
    {
        this.data = data;
        this.board = board;
        this.position = position;

        rotationIndex = 0;
        stepTime = Time.time + stepDelay;
        moveTime = Time.time + moveDelay;
        lockTime = 0f;

        if (cells == null) {
            cells = new Vector3Int[data.cells.Length];
        }

        for (int i = 0; i < cells.Length; i++) {
            cells[i] = (Vector3Int)data.cells[i];
        }
        ConnectToTCPServer();
    }

    private void Update()
    {
        board.Clear(this);

        // Handle TCP inputs
        if (!string.IsNullOrEmpty(lastMessage))
        {
            HandleTCPInput(lastMessage);
            lastMessage = null;
        }

        // Once the piece has been inactive for too long it becomes locked
        lockTime += Time.deltaTime;

        // Advance the piece to the next row every x seconds
        if (Time.time > moveTime)
        {
            HandleContinuousInput();
        }

        if (Time.time > stepTime)
        {
            Step();
        }

        board.Set(this);
    }

    private void HandleTCPInput(string message)
    {
        Debug.Log($"Received TCP Message: {message}");
        currentInputState = message;
        switch (message)
        {

            case "Leaning Left":
                Move(Vector2Int.left);
                cameraEffect.TriggerState("Leaning Left");
                break;
            case "Leaning Right":
                Move(Vector2Int.right);
                cameraEffect.TriggerState("Leaning Right");
                break;
            case "Leaning Forward":
                Rotate(1);
                cameraEffect.TriggerState("Neutral");
                break;
            case "Leaning Backward":
                cameraEffect.TriggerState("Neutral");
                break;
            case "shake":
                DestroyPiece(); // Rotate clockwise
                cameraEffect.TriggerState("Neutral");
                break;
            case "Button Pressed":
                Rotate(-1); // Rotate counterclockwise
                break;
            case "Neutral":
                cameraEffect.TriggerState("Neutral");
                break;
            case "Button Released":
                // No specific action for button released
                break;
        }
    }

    private void HandleContinuousInput()
    {
        if (currentInputState == "Leaning Backward")
        {
            Step(); // Accelerate drop
        }
        moveTime = Time.time + moveDelay; // Reset move delay
    }

    private void Step()
    {
        stepTime = Time.time + stepDelay;

        // Step down to the next row
        Move(Vector2Int.down);

        // Once the piece has been inactive for too long it becomes locked
        if (lockTime >= lockDelay){
            Lock();
        }
    }

    private void HardDrop()
    {
        while (Move(Vector2Int.down)) {
            continue;
        }

        Lock();
    }

    private void Lock()
    {
        board.Set(this);
        board.ClearLines();
        board.SpawnPiece();
    }

    private void DestroyPiece()
    {
        board.Clear(this);

        foreach (Vector3Int cell in cells)
        {
            Vector3Int tilePosition = cell + position;
            Vector3 worldPosition = board.tilemap.CellToWorld(tilePosition);
            worldPosition += board.tilemap.cellSize / 2;
            GameObject burstInstance = Instantiate(burst, worldPosition, Quaternion.identity);
            Destroy(burstInstance, 1);
        }

        board.SpawnPiece();
        lockTime = 0f;
        stepTime = Time.time + stepDelay;
        moveTime = Time.time + moveDelay;

        Debug.Log("Current piece destroyed and replaced with a new piece.");
    }

    private bool Move(Vector2Int translation)
    {
        Vector3Int newPosition = position;
        newPosition.x += translation.x;
        newPosition.y += translation.y;

        bool valid = board.IsValidPosition(this, newPosition);

        // Only save the movement if the new position is valid
        if (valid)
        {
            position = newPosition;
            moveTime = Time.time + moveDelay;
            lockTime = 0f; // reset
        }

        return valid;
    }

    private void Rotate(int direction)
    {
        // Store the current rotation in case the rotation fails
        // and we need to revert
        int originalRotation = rotationIndex;

        // Rotate all of the cells using a rotation matrix
        rotationIndex = Wrap(rotationIndex + direction, 0, 4);
        ApplyRotationMatrix(direction);

        // Revert the rotation if the wall kick tests fail
        if (!TestWallKicks(rotationIndex, direction))
        {
            rotationIndex = originalRotation;
            ApplyRotationMatrix(-direction);
        }
    }

    private void ApplyRotationMatrix(int direction)
    {
        float[] matrix = Data.RotationMatrix;

        // Rotate all of the cells using the rotation matrix
        for (int i = 0; i < cells.Length; i++)
        {
            Vector3 cell = cells[i];

            int x, y;

            switch (data.tetromino)
            {
                case Tetromino.I:
                case Tetromino.O:
                    // "I" and "O" are rotated from an offset center point
                    cell.x -= 0.5f;
                    cell.y -= 0.5f;
                    x = Mathf.CeilToInt((cell.x * matrix[0] * direction) + (cell.y * matrix[1] * direction));
                    y = Mathf.CeilToInt((cell.x * matrix[2] * direction) + (cell.y * matrix[3] * direction));
                    break;

                default:
                    x = Mathf.RoundToInt((cell.x * matrix[0] * direction) + (cell.y * matrix[1] * direction));
                    y = Mathf.RoundToInt((cell.x * matrix[2] * direction) + (cell.y * matrix[3] * direction));
                    break;
            }

            cells[i] = new Vector3Int(x, y, 0);
        }
    }

    private bool TestWallKicks(int rotationIndex, int rotationDirection)
    {
        int wallKickIndex = GetWallKickIndex(rotationIndex, rotationDirection);

        for (int i = 0; i < data.wallKicks.GetLength(1); i++)
        {
            Vector2Int translation = data.wallKicks[wallKickIndex, i];

            if (Move(translation)) {
                return true;
            }
        }

        return false;
    }

    private int GetWallKickIndex(int rotationIndex, int rotationDirection)
    {
        int wallKickIndex = rotationIndex * 2;

        if (rotationDirection < 0) {
            wallKickIndex--;
        }

        return Wrap(wallKickIndex, 0, data.wallKicks.GetLength(0));
    }

    private int Wrap(int input, int min, int max)
    {
        if (input < min) {
            return max - (min - input) % (max - min);
        } else {
            return min + (input - min) % (max - min);
        }
    }

    private void ConnectToTCPServer()
    {
        try
        {
            tcpClient = new TcpClient("127.0.0.1", 65432);
            reader = new StreamReader(tcpClient.GetStream());
            tcpThread = new Thread(ListenForTCPMessages);
            tcpThread.IsBackground = true;
            tcpThread.Start();
            Debug.Log("Connected to TCP Server.");
        }
        catch (System.Exception e)
        {
            Debug.Log($"Error connecting to TCP Server: {e.Message}");
        }
    }

    private void ListenForTCPMessages()
    {
        try
        {
            while (true)
            {
                string message = reader.ReadLine();
                if (!string.IsNullOrEmpty(message))
                {
                    lastMessage = message;
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.Log($"Disconnected from TCP Server: {e.Message}");
        }
    }

    private void OnDestroy()
    {
        if (tcpClient != null)
        {
            reader.Close();
            tcpClient.Close();
        }

        if (tcpThread != null)
        {
            tcpThread.Abort();
        }
    }
}
